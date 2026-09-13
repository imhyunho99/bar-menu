"""
Sentry 로 무엇을 올리고 무엇을 버리는가.

settings.py 안에 있던 것을 옮겼다. 거기서는 `if SENTRY_DSN:` 블록 안의
중첩 함수라 import 할 수 없었고, import 할 수 없으면 테스트할 수 없었다.
'무엇을 버리는가' 는 조용히 틀리는 종류의 판단이라 테스트가 필요하다.

settings 는 이 모듈을 **함수 안에서 늦게** import 한다. settings 로드 시점에
menu 패키지를 끌어오면 앱 준비 전에 모델이 딸려 들어올 위험이 있다.
"""

import logging

logger = logging.getLogger(__name__)

# uwsgi 가 응답을 클라이언트 소켓에 쓰다 실패하면 내는 메시지. 디스크가 아니라
# 네트워크 쪽 write 다. 봇이 400 응답을 다 읽기 전에 끊으면 이게 난다.
_UWSGI_CLIENT_GONE = 'write error'


def is_client_disconnect(exc):
    """
    받는 쪽이 사라져서 난 예외인가.

    서버가 잘못한 게 아니고 손님 화면에도 영향이 없다. 스캐너가 하루에도
    몇 번씩 만들어 내므로 걸러내지 않으면 진짜 에러가 그 사이에 묻힌다.

    OSError 를 통째로 버리지 않는 것이 이 함수의 요점이다. 디스크가 차면
    같은 OSError 로 사진 저장이 실패하는데, 그건 반드시 알아야 한다.
    그래서 errno 가 없는 uwsgi 특유의 'write error' 와, 끊김을 뜻하는
    전용 예외 클래스만 고른다.
    """
    if isinstance(exc, (BrokenPipeError, ConnectionResetError, ConnectionAbortedError)):
        return True
    if type(exc) is OSError and exc.errno is None:
        return str(exc) == _UWSGI_CLIENT_GONE
    return False


def before_send(event, hint):
    """Sentry 로 보내기 직전. None 을 돌려주면 그 이벤트는 버려진다."""
    exc_info = hint.get('exc_info')
    exc = exc_info[1] if exc_info else None

    # 봇이 잘못된 Host 헤더로 접근할 때 나는 DisallowedHost 는 무시한다.
    if exc_info and exc_info[0].__name__ == 'DisallowedHost':
        return None

    if exc is not None and is_client_disconnect(exc):
        return None

    # error/fatal 이벤트는 Discord 에러 웹훅으로도 알린다(best-effort).
    # 알림 발송 실패 로그(menu.notifications)는 제외해 무한루프를 막는다.
    if event.get('level') in ('error', 'fatal') and event.get('logger') != 'menu.notifications':
        try:
            from menu.notifications import send_error_alert
            send_error_alert(event, hint)
        except Exception:
            # 알림이 실패해도 Sentry 기록은 남겨야 한다. 여기서 예외가 새면
            # 이벤트가 통째로 사라진다.
            logger.debug('Discord 에러 알림 발송에 실패했습니다', exc_info=True)

    return event
