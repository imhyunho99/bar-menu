"""
종이 메뉴판 사진을 읽어 카테고리·메뉴 구조로 옮긴다.

사장님이 기존 메뉴판을 찍어 올리면 Claude 비전이 항목을 뽑아내고,
어드민은 그 결과를 확인·수정한 뒤 저장한다. 바로 DB에 쓰지 않는 이유는
OCR이 가격 한 자리를 틀리는 것만으로도 손님 화면이 틀어지기 때문이다.
"""

import base64
import io
import logging
import os

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Claude 비전은 긴 변 2576px 까지 받는다. 그보다 큰 사진은 토큰만 더 쓰고
# 읽히는 글자는 같아서 미리 줄인다.
MAX_EDGE_PX = 2000

# 압축 폭탄 방어. PIL 기본 MAX_IMAGE_PIXELS(89M)는 2배를 넘어야 예외를 내고
# 그 아래는 경고만 하고 디코딩한다. 440KB 짜리 12000x12000 PNG 한 장이
# 수백 MB를 먹는데 운영 인스턴스는 RAM 1GB 미만이라 그대로 죽는다.
# 요즘 폰 사진이 4032x3024(12M)라 40M면 충분히 넉넉하다.
MAX_PIXELS = 40_000_000
MAX_UPLOAD_BYTES = 12 * 1024 * 1024

# 한 번에 올릴 수 있는 장수. 사장님께 보이는 규칙은 이것 하나다 — 용량은
# 폰에서 확인할 방법이 없어서 "10장" 만큼 이해되지 않는다. 합계 용량은
# 아래 상한이 조용히 막고, Discord 로 보낼 때의 분할은 notifications 가 맡는다.
MAX_IMAGES = 10

# nginx 의 client_max_body_size 는 20MB 다. 거기서 막히면 사장님은 뜻 모를
# 413 을 본다. 그 앞에서 우리말로 안내하려고 조금 낮게 잡는다.
MAX_TOTAL_UPLOAD_BYTES = 18 * 1024 * 1024

# 메뉴판 한 장이 60~80개 항목까지 갈 수 있다. thinking 과 출력이 max_tokens 를
# 함께 나눠 쓰므로 넉넉히 잡는다.
MAX_TOKENS = 16000

MODEL = "claude-opus-5"

# SDK 기본 타임아웃은 10분이고, 이 호출은 요청 스레드를 붙잡은 채로 기다린다.
# 운영은 uwsgi 워커 2개라 임포트 두 건이 겹치면 사이트 전체가 멈춘다.
# 메뉴판 한 장은 이 안에 끝난다. 못 끝내면 기다리는 쪽이 손해다.
REQUEST_TIMEOUT_SECONDS = 120.0

SYSTEM_PROMPT = """당신은 종이 메뉴판 사진을 읽어 구조화하는 일을 합니다.

사진에 보이는 것만 옮깁니다. 읽히지 않는 글자를 그럴듯하게 메우지 말고,
없는 항목을 만들어내지 마십시오. 확실하지 않은 항목은 confident 를 false 로 둡니다.

가격은 사진에 적힌 표기를 그대로 옮깁니다. 통화 기호나 '원'은 빼고 숫자와
구분 기호만 남깁니다 (예: "15,000" 또는 "15.5"). 시가·문의처럼 숫자가 아닌
표기는 적힌 그대로 둡니다.

카테고리 구분선이 없는 메뉴판이면 카테고리 하나에 전부 담습니다.
없는 정보(영문명, 설명)는 빈 문자열로 둡니다."""


class ParsedItem(BaseModel):
    name: str = Field(description="메뉴명. 사진에 적힌 그대로")
    name_en: str = Field(default="", description="영문명. 사진에 없으면 빈 문자열")
    price: str = Field(default="", description="가격 표기. 통화 기호 제외")
    description: str = Field(default="", description="메뉴 설명. 없으면 빈 문자열")
    confident: bool = Field(
        default=True,
        description="글자가 또렷하게 읽혔으면 true, 흐리거나 가려져 추측했으면 false",
    )


class ParsedCategory(BaseModel):
    name: str = Field(description="카테고리명. 사진에 구분이 없으면 '메뉴'")
    name_en: str = Field(default="")
    items: list[ParsedItem]


class ParsedMenu(BaseModel):
    categories: list[ParsedCategory]
    notes: str = Field(
        default="",
        description="사장님이 확인해야 할 점 (가려진 부분, 판독이 어려운 구역 등). 없으면 빈 문자열",
    )


class MenuImportError(Exception):
    """업로드한 사진을 메뉴로 옮기지 못했다."""


def shrink_for_vision(image_bytes: bytes) -> tuple[bytes, str]:
    """긴 변을 MAX_EDGE_PX 로 줄이고 JPEG 로 통일한다."""
    from PIL import Image

    if len(image_bytes) > MAX_UPLOAD_BYTES:
        raise MenuImportError(
            f"사진이 너무 큽니다. {MAX_UPLOAD_BYTES // (1024 * 1024)}MB 이하로 올려 주세요."
        )

    # Image.open 은 헤더만 읽는다. 크기를 먼저 보고 거른 뒤에 디코딩해야
    # 압축 폭탄이 convert() 에서 메모리를 통째로 먹는 일을 막을 수 있다.
    try:
        im = Image.open(io.BytesIO(image_bytes))
    except Exception as exc:
        raise MenuImportError("이미지 파일을 열 수 없습니다. jpg/png 파일인지 확인해 주세요.") from exc

    if im.width * im.height > MAX_PIXELS:
        raise MenuImportError(
            f"사진 해상도가 너무 큽니다 ({im.width}x{im.height}). "
            "휴대폰으로 찍은 사진 그대로 올려 주세요."
        )

    try:
        im = im.convert("RGB")
    except Exception as exc:
        raise MenuImportError("이미지를 읽지 못했습니다. 다른 사진으로 시도해 주세요.") from exc

    if max(im.size) > MAX_EDGE_PX:
        ratio = MAX_EDGE_PX / max(im.size)
        im = im.resize((round(im.width * ratio), round(im.height * ratio)), Image.LANCZOS)

    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=85, optimize=True)
    return buf.getvalue(), "image/jpeg"


def parse_menu_image(image_bytes: bytes) -> ParsedMenu:
    """메뉴판 사진 한 장을 ParsedMenu 로 옮긴다."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise MenuImportError("ANTHROPIC_API_KEY 가 설정되어 있지 않습니다.")

    try:
        import anthropic
    except ImportError as exc:
        raise MenuImportError("anthropic 패키지가 설치되어 있지 않습니다.") from exc

    payload, media_type = shrink_for_vision(image_bytes)
    encoded = base64.standard_b64encode(payload).decode("utf-8")

    client = anthropic.Anthropic(timeout=REQUEST_TIMEOUT_SECONDS, max_retries=1)
    try:
        response = client.messages.parse(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": encoded,
                            },
                        },
                        {
                            "type": "text",
                            "text": "이 메뉴판을 카테고리와 메뉴 항목으로 옮겨 주세요.",
                        },
                    ],
                }
            ],
            output_format=ParsedMenu,
        )
    except anthropic.APIStatusError as exc:
        logger.warning("menu import: Claude API error %s", exc.status_code)
        raise MenuImportError(f"메뉴판 인식 요청이 실패했습니다. (오류 {exc.status_code})") from exc
    except anthropic.APITimeoutError as exc:
        raise MenuImportError(
            "메뉴판 인식이 시간 안에 끝나지 않았습니다. 사진을 두세 장으로 나눠 올려 주세요."
        ) from exc
    except anthropic.APIConnectionError as exc:
        raise MenuImportError("메뉴판 인식 서버에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.") from exc

    # 안전 분류기가 요청을 거절하면 content 가 비어 있다. parsed_output 을
    # 바로 읽으면 그 자리에서 터지므로 stop_reason 을 먼저 본다.
    if response.stop_reason == "refusal":
        raise MenuImportError("이 사진은 처리할 수 없습니다. 다른 사진으로 시도해 주세요.")
    if response.stop_reason == "max_tokens":
        raise MenuImportError(
            "메뉴판이 너무 길어 한 번에 옮기지 못했습니다. 사진을 두세 장으로 나눠 올려 주세요."
        )

    parsed = response.parsed_output
    if parsed is None:
        raise MenuImportError("메뉴판에서 항목을 찾지 못했습니다. 사진이 또렷한지 확인해 주세요.")

    return parsed
