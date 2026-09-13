"""
Sentry 로 무엇을 올리고 무엇을 버리는가.

노이즈를 안 거르면 진짜 에러가 그 사이에 묻힌다. 반대로 넓게 거르면
진짜 에러까지 조용히 사라진다 — 그게 더 나쁘다. 경계를 여기서 못박는다.
"""

from unittest.mock import patch

from django.core.exceptions import DisallowedHost
from django.test import TestCase

from menu.observability import before_send, is_client_disconnect


def _hint(exc):
    return {'exc_info': (type(exc), exc, None)}


class ClientDisconnectsAreDroppedTests(TestCase):
    """
    봇이 응답을 다 읽기 전에 끊으면 uwsgi 가 'OSError: write error' 를 낸다.
    서버가 잘못한 게 아니라 받는 쪽이 사라진 것이라 손님에게 영향이 없다.
    """

    def test_uwsgi_write_error_is_a_client_disconnect(self):
        self.assertTrue(is_client_disconnect(OSError('write error')))

    def test_broken_pipe_is_a_client_disconnect(self):
        self.assertTrue(is_client_disconnect(BrokenPipeError(32, 'Broken pipe')))

    def test_connection_reset_is_a_client_disconnect(self):
        self.assertTrue(is_client_disconnect(ConnectionResetError(104, 'Connection reset by peer')))

    def test_a_full_disk_is_not_a_client_disconnect(self):
        """
        여기가 이 필터의 전부다. OSError 를 통째로 버리면 디스크가 찼을 때
        아무도 모른 채 사진 저장이 실패한다.
        """
        self.assertFalse(is_client_disconnect(OSError(28, 'No space left on device')))

    def test_a_permission_error_is_not_a_client_disconnect(self):
        self.assertFalse(is_client_disconnect(PermissionError(13, 'Permission denied')))

    def test_an_unrelated_exception_is_not_a_client_disconnect(self):
        self.assertFalse(is_client_disconnect(ValueError('그냥 버그')))


class BeforeSendTests(TestCase):
    def test_disallowed_host_is_dropped(self):
        """봇이 IP 로 직접 들어오면 난다. 정상 동작이지 에러가 아니다."""
        self.assertIsNone(before_send({}, _hint(DisallowedHost('bad host'))))

    def test_a_client_disconnect_is_dropped(self):
        self.assertIsNone(before_send({}, _hint(OSError('write error'))))

    def test_a_full_disk_still_reaches_sentry(self):
        event = {'level': 'error'}
        with patch('menu.notifications.send_error_alert'):
            self.assertIsNotNone(before_send(event, _hint(OSError(28, 'No space left on device'))))

    def test_a_real_error_reaches_sentry_and_discord(self):
        event = {'level': 'error'}
        with patch('menu.notifications.send_error_alert') as alert:
            self.assertIs(before_send(event, _hint(ValueError('진짜 버그'))), event)
        alert.assert_called_once()

    def test_notification_failures_do_not_loop_back_to_discord(self):
        """
        Discord 발송 실패를 Discord 로 알리면 실패할 때마다 다시 실패한다.
        """
        event = {'level': 'error', 'logger': 'menu.notifications'}
        with patch('menu.notifications.send_error_alert') as alert:
            self.assertIs(before_send(event, _hint(OSError('보내기 실패'))), event)
        alert.assert_not_called()

    def test_an_event_without_exc_info_is_kept(self):
        """로그만으로 올라온 이벤트. 예외가 없다고 버릴 이유는 없다."""
        event = {'level': 'warning'}
        self.assertIs(before_send(event, {}), event)

    def test_a_broken_discord_webhook_does_not_swallow_the_event(self):
        """알림이 실패해도 Sentry 기록은 남아야 한다."""
        event = {'level': 'error'}
        with patch('menu.notifications.send_error_alert', side_effect=RuntimeError('웹훅 죽음')):
            self.assertIs(before_send(event, _hint(ValueError('진짜 버그'))), event)
