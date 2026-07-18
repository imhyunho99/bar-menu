"""제휴 문의 접수 시 Discord 웹훅으로 알림을 보낸다.

발송은 best-effort다. 웹훅이 느리거나 실패해도 문의 저장과 API 응답에는
영향을 주지 않도록, 별도 데몬 스레드에서 처리하고 예외를 삼킨다.
`DISCORD_WEBHOOK_URL` 환경변수가 없으면(예: 스테이징) 아무것도 하지 않는다.
"""
import json
import logging
import os
import threading
import urllib.request

logger = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 5


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
