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
