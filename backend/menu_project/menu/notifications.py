"""제휴 문의 접수 시 Discord 웹훅으로 알림을 보낸다.

발송은 best-effort다. 웹훅이 느리거나 실패해도 문의 저장과 API 응답에는
영향을 주지 않도록, 별도 데몬 스레드에서 처리하고 예외를 삼킨다.
`DISCORD_WEBHOOK_URL` 환경변수가 없으면(예: 스테이징) 아무것도 하지 않는다.
"""
import json
import logging
import os
import threading
import time
import urllib.request

logger = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 5

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
