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

# 메뉴판 한 장이 60~80개 항목까지 갈 수 있다. thinking 과 출력이 max_tokens 를
# 함께 나눠 쓰므로 넉넉히 잡는다.
MAX_TOKENS = 16000

MODEL = "claude-opus-5"

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

    try:
        im = Image.open(io.BytesIO(image_bytes))
        im = im.convert("RGB")
    except Exception as exc:
        raise MenuImportError("이미지 파일을 열 수 없습니다. jpg/png 파일인지 확인해 주세요.") from exc

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

    client = anthropic.Anthropic()
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
