"""제휴 문의 접수 시 Discord 웹훅으로 알림을 보낸다.

발송은 best-effort다. 웹훅이 느리거나 실패해도 문의 저장과 API 응답에는
영향을 주지 않도록, 별도 데몬 스레드에서 처리하고 예외를 삼킨다.
`DISCORD_WEBHOOK_URL` 환경변수가 없으면(예: 스테이징) 아무것도 하지 않는다.
"""
import hashlib
import json
import logging
import os
import threading
import time
import urllib.request

logger = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 5

# 사진 여러 장은 5초 안에 못 올라간다. 이 발송만 요청 스레드를 붙잡으므로
# 무한정 기다리게 두면 워커 하나가 통째로 묶인다.
_PHOTO_TIMEOUT_SECONDS = 60

# 같은 에러가 짧은 시간에 반복될 때 Discord 알림이 폭탄이 되지 않도록,
# (에러종류, 메시지) 단위로 이 창(초) 안에는 한 번만 보낸다. 워커 프로세스별로 관리한다.
_ERROR_DEDUP_WINDOW = 60
_error_last_sent = {}


def build_contact_payload(submission):
    """ContactSubmission을 Discord 웹훅 JSON 페이로드로 변환한다."""
    return {
        "embeds": [
            {
                "title": "📩 새 제휴 문의",
                "color": 5814783,
                "fields": [
                    {"name": "이름/업체명", "value": submission.name or "-", "inline": True},
                    {"name": "연락처", "value": submission.contact_info or "-", "inline": True},
                    {"name": "요금제", "value": submission.plan or "-", "inline": False},
                ],
                "timestamp": submission.created_at.isoformat(),
            }
        ]
    }


def _build_request(url, payload):
    data = json.dumps(payload).encode("utf-8")
    return urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            # Discord 앞단 Cloudflare는 기본 "Python-urllib/x" User-Agent를
            # 봇으로 보고 403을 반환한다. 커스텀 UA로 우회한다.
            "User-Agent": "bar-menu-contact-webhook/1.0",
        },
    )


def _post(url, payload):
    """웹훅 URL로 페이로드를 POST한다. 실패 시 예외를 던진다(호출부에서 처리)."""
    urllib.request.urlopen(_build_request(url, payload), timeout=_TIMEOUT_SECONDS)


def _deliver(url, payload):
    try:
        _post(url, payload)
    except Exception:
        logger.exception("Discord 제휴 문의 알림 발송 실패")


def send_contact_notification(submission):
    """문의 알림을 비동기로 발송한다.

    `DISCORD_WEBHOOK_URL`이 없으면 None을 반환하고 아무것도 하지 않는다.
    설정돼 있으면 발송 스레드를 시작하고 그 Thread를 반환한다(테스트에서 join 가능).
    """
    url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not url:
        return None
    payload = build_contact_payload(submission)
    thread = threading.Thread(target=_deliver, args=(url, payload), daemon=True)
    thread.start()
    return thread


def build_error_payload(event, hint):
    """Sentry 이벤트를 Discord 에러 알림 페이로드로 변환한다."""
    values = (event.get("exception") or {}).get("values") or [{}]
    last = values[-1]
    error_type = last.get("type") or event.get("level", "error")
    error_value = last.get("value") or event.get("message") or "(메시지 없음)"
    return {
        "embeds": [
            {
                "title": f"🚨 서버 에러: {error_type}"[:250],
                "description": str(error_value)[:1500],
                "color": 15158332,
                "fields": [
                    {"name": "위치", "value": (event.get("transaction") or "-")[:200], "inline": True},
                    {"name": "환경", "value": (event.get("environment") or "-")[:100], "inline": True},
                ],
            }
        ]
    }


def _error_is_throttled(event):
    """같은 에러가 dedup 창 안에 이미 보내졌으면 True."""
    values = (event.get("exception") or {}).get("values") or [{}]
    last = values[-1]
    key = (last.get("type"), last.get("value") or event.get("message"))
    now = time.monotonic()
    last_sent = _error_last_sent.get(key)
    if last_sent is not None and now - last_sent < _ERROR_DEDUP_WINDOW:
        return True
    _error_last_sent[key] = now
    return False


def send_error_alert(event, hint=None):
    """Sentry error/fatal 이벤트를 Discord 에러 웹훅으로 비동기 발송한다.

    `DISCORD_ERROR_WEBHOOK_URL`이 없거나 dedup 창에 걸리면 None을 반환한다.
    """
    url = os.environ.get("DISCORD_ERROR_WEBHOOK_URL")
    if not url:
        return None
    if _error_is_throttled(event):
        return None
    payload = build_error_payload(event, hint)
    thread = threading.Thread(target=_deliver, args=(url, payload), daemon=True)
    thread.start()
    return thread


# ── 무료 체험 (가입 · 만료) ────────────────────────────────────────────
# 결제 대행사가 붙기 전까지 청구는 사람이 한다. 그 사람이 움직일 수 있으려면
# 두 순간을 알아야 한다: 누가 들어왔는가, 누구의 체험이 끝났는가. 그래서
# 페이로드는 언제나 연락 수단을 싣는다 — 알림을 받고도 연락할 곳이 없으면
# 알림이 아니라 소음이다.

def _owner_contact(restaurant):
    """
    매장 사장님의 이메일과 전화. 없으면 '-'.

    어드민에서 매장만 먼저 만드는 경로가 있어서 관리자가 아직 없을 수 있다.
    거기서 예외가 나면 매장 생성 자체가 막히므로 조용히 비운다.
    """
    profile = restaurant.managers.select_related('user').first()
    if profile is None:
        return '-', '-'
    return (profile.user.email or profile.user.username or '-'), (profile.phone or '-')


def build_signup_payload(restaurant):
    """새로 가입한 매장을 Discord 웹훅 JSON 페이로드로 변환한다."""
    email, phone = _owner_contact(restaurant)
    subscription = getattr(restaurant, 'subscription', None)
    ends_at = getattr(subscription, 'current_period_end', None)
    return {
        "embeds": [
            {
                "title": "🌱 새 매장 가입 (무료 체험 시작)",
                "color": 3066993,
                "fields": [
                    {"name": "매장명", "value": restaurant.name or "-", "inline": True},
                    {"name": "주소", "value": f"/{restaurant.slug}", "inline": True},
                    {"name": "이메일", "value": email, "inline": False},
                    {"name": "연락처", "value": phone, "inline": True},
                    {"name": "체험 종료",
                     "value": f'{ends_at:%Y-%m-%d %H:%M}' if ends_at else "-", "inline": True},
                ],
            }
        ]
    }


def build_trial_expired_payload(subscription):
    """체험이 끝난 매장을 Discord 웹훅 JSON 페이로드로 변환한다."""
    restaurant = subscription.restaurant
    email, phone = _owner_contact(restaurant)
    return {
        "embeds": [
            {
                "title": "⏰ 무료 체험 종료 — 손님 화면이 닫혔습니다",
                "description": "결제 안내가 필요합니다. 사장님이 먼저 연락하지 않는 쪽이 보통입니다.",
                "color": 15105570,
                "fields": [
                    {"name": "매장명", "value": restaurant.name or "-", "inline": True},
                    {"name": "주소", "value": f"/{restaurant.slug}", "inline": True},
                    {"name": "이메일", "value": email, "inline": False},
                    {"name": "연락처", "value": phone, "inline": True},
                    {"name": "요금제", "value": subscription.get_plan_display(), "inline": True},
                ],
            }
        ]
    }


def _send(payload):
    """제휴 문의와 같은 채널로 보낸다. 둘 다 '사람이 이어받아야 하는 일'이다."""
    url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not url:
        return None
    thread = threading.Thread(target=_deliver, args=(url, payload), daemon=True)
    thread.start()
    return thread


def send_signup_notification(restaurant):
    """가입 알림을 비동기로 발송한다. 웹훅이 없으면 아무것도 하지 않는다."""
    return _send(build_signup_payload(restaurant))


def send_trial_expired_notification(subscription):
    """체험 종료 알림을 비동기로 발송한다. 웹훅이 없으면 아무것도 하지 않는다."""
    return _send(build_trial_expired_payload(subscription))


# ── 메뉴판 사진 중계 ───────────────────────────────────────────────────
# 비전 API 로 자동 인식하는 대신, 사장님이 올린 사진을 우리에게 그대로 보내고
# 사람이 정리해 넣는다. 그래서 이 발송만 다른 알림과 다르게 동기로 돈다 —
# 도착 여부를 호출자가 알아야 하기 때문이다. 다른 알림은 못 가도 로그만 남으면
# 되지만, 이건 못 갔는데 사장님에게 '받았습니다' 가 뜨면 아무도 눈치채지 못한 채
# 사장님만 기다린다.

# Discord 기본 업로드 한도는 파일당 10 MiB 다. 메시지 총량은 문서에 없어서
# 넉넉히 아래로 잡고, 넘으면 거절하지 않고 메시지를 나눠 보낸다 — 몇 MB 인지는
# 사장님이 알 필요 없는 우리 사정이다.
_DISCORD_BATCH_BYTES = 8 * 1024 * 1024


def build_menu_photo_payload(restaurant, count, part=None, parts=None):
    """사진과 함께 보낼 설명. 연락처가 없으면 되물을 방법이 없어 반드시 싣는다."""
    email, phone = _owner_contact(restaurant)
    title = "🧾 메뉴판 사진이 도착했습니다"
    if parts and parts > 1:
        title += f" ({part}/{parts})"
    return {
        "embeds": [
            {
                "title": title,
                "description": "사장님이 올린 메뉴판입니다. 정리해서 넣어 준 뒤 사장님께 알려 주세요.",
                "color": 3447003,
                "fields": [
                    {"name": "매장명", "value": restaurant.name or "-", "inline": True},
                    {"name": "주소", "value": f"/{restaurant.slug}", "inline": True},
                    {"name": "이메일", "value": email, "inline": False},
                    {"name": "연락처", "value": phone, "inline": True},
                    {"name": "장수", "value": f"{count}장", "inline": True},
                ],
            }
        ]
    }


def _multipart(payload, images, start_index):
    """Discord 가 받는 multipart/form-data 를 만든다. 경계 문자열은 본문에 없어야 한다."""
    boundary = "----barmenu" + hashlib.sha256(
        b"".join(img[:64] for img in images) + str(start_index).encode()
    ).hexdigest()[:24]
    sep = f"--{boundary}\r\n".encode()
    body = bytearray()
    body += sep
    body += b'Content-Disposition: form-data; name="payload_json"\r\n'
    body += b"Content-Type: application/json\r\n\r\n"
    body += json.dumps(payload).encode("utf-8") + b"\r\n"
    for i, image in enumerate(images):
        body += sep
        body += (
            f'Content-Disposition: form-data; name="files[{i}]"; '
            f'filename="menu-{start_index + i + 1}.jpg"\r\n'
        ).encode()
        body += b"Content-Type: image/jpeg\r\n\r\n"
        body += image + b"\r\n"
    body += f"--{boundary}--\r\n".encode()
    return bytes(body), f"multipart/form-data; boundary={boundary}"


def _batch(images):
    """Discord 한 메시지에 담을 만큼씩 끊는다. 한 장이 한도를 넘어도 혼자는 보낸다."""
    batches, current, size = [], [], 0
    for image in images:
        if current and size + len(image) > _DISCORD_BATCH_BYTES:
            batches.append(current)
            current, size = [], 0
        current.append(image)
        size += len(image)
    if current:
        batches.append(current)
    return batches


def send_menu_photos(restaurant, images) -> bool:
    """
    메뉴판 사진을 Discord 로 보낸다. **동기**로 돌고 도착 여부를 돌려준다.

    한 묶음이라도 실패하면 False. 일부만 도착한 채 True 를 주면 우리는
    나머지 장을 영영 못 보고, 사장님은 메뉴가 반만 들어간 이유를 모른다.
    """
    url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not url:
        logger.error("메뉴판 사진을 보낼 DISCORD_WEBHOOK_URL 이 없습니다 (매장 %s)", restaurant.slug)
        return False

    batches = _batch(images)
    sent = 0
    for part, group in enumerate(batches, start=1):
        payload = build_menu_photo_payload(restaurant, len(images), part, len(batches))
        body, content_type = _multipart(payload, group, sent)
        request = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": content_type, "User-Agent": "bar-menu-contact-webhook/1.0"},
        )
        try:
            urllib.request.urlopen(request, timeout=_PHOTO_TIMEOUT_SECONDS)
        except Exception:
            logger.exception("메뉴판 사진 전송 실패 (매장 %s, %d/%d)",
                             restaurant.slug, part, len(batches))
            return False
        sent += len(group)
    return True
