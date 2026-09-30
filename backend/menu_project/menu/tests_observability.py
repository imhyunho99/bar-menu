"""
Sentry 로 무엇을 올리고 무엇을 버리는가.

노이즈를 안 거르면 진짜 에러가 그 사이에 묻힌다. 반대로 넓게 거르면
진짜 에러까지 조용히 사라진다 — 그게 더 나쁘다. 경계를 여기서 못박는다.
"""

from unittest.mock import patch

from django.core.exceptions import DisallowedHost
from django.test import TestCase

from menu import notifications, observability
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


class DisconnectEventsWithoutAnExceptionObjectTests(TestCase):
    """
    로깅 통합으로 들어온 이벤트에는 hint 에 exc_info 가 없을 수 있다. 그러면
    예외 객체를 보는 검사가 볼 것이 없어 통과해 버린다 — 정작 가장 자주 오는
    'OSError: write error' 가 그 모양으로 올라올 수 있다.

    2026-09-27 운영 로그 확인: 30일간 Broken pipe 가 스캐너(phpunit 취약점
    탐색, /actuator/configprops 등)와 빠른 크롤러 한 곳에서 났다. 전부
    받는 쪽이 먼저 끊은 것이고 서버가 잘못한 것이 아니다.
    """

    def _event(self, exc_type, value):
        return {'exception': {'values': [{'type': exc_type, 'value': value}]}}

    def test_a_uwsgi_write_error_is_dropped(self):
        self.assertIsNone(before_send(self._event('OSError', 'write error'), {}))

    def test_broken_pipe_by_name_is_dropped(self):
        for name in ('BrokenPipeError', 'ConnectionResetError', 'ConnectionAbortedError'):
            with self.subTest(name=name):
                self.assertIsNone(before_send(self._event(name, '[Errno 32]'), {}))

    def test_a_real_oserror_still_gets_through(self):
        """디스크가 차서 사진 저장이 실패하는 것은 반드시 알아야 한다."""
        event = self._event('OSError', '[Errno 28] No space left on device')
        self.assertIsNotNone(before_send(event, {}))

    def test_an_unrelated_error_still_gets_through(self):
        self.assertIsNotNone(before_send(self._event('ValueError', 'nope'), {}))

    def test_an_event_with_no_exception_is_untouched(self):
        self.assertIsNotNone(before_send({'level': 'warning'}, {}))


class TheErrorAlertSaysEnoughToActOnTests(TestCase):
    """
    예전 알림은 '위치' 와 '환경' 둘뿐이었다. 그런데 자주 오는 에러일수록
    transaction 이 비어서(응답을 쓰다 난 것이라 뷰가 특정되지 않는다)
    `위치 -` 만 남았다. 받는 사람은 Sentry 를 따로 열어 찾아야 했고,
    사용자가 실제로 그 상태를 보고 있었다.
    """

    def _payload(self, event):
        return notifications.build_error_payload(event, None)['embeds'][0]

    def _field(self, embed, name):
        return next((f['value'] for f in embed['fields'] if f['name'] == name), None)

    def test_it_carries_the_request_that_failed(self):
        embed = self._payload({
            'exception': {'values': [{'type': 'OSError', 'value': 'write error'}]},
            'request': {'method': 'GET', 'url': 'https://bar-menu.ddnsfree.com/bid/category/11/'},
        })
        self.assertIn('/bid/category/11/', self._field(embed, '요청'))

    def test_it_carries_who_sent_it(self):
        """스캐너인지 손님인지가 대개 IP 와 User-Agent 에서 갈린다."""
        embed = self._payload({
            'exception': {'values': [{'type': 'OSError', 'value': 'write error'}]},
            'user': {'ip_address': '213.209.159.84'},
            'request': {'headers': {'User-Agent': 'curl/8.4.0'}},
        })
        sender = self._field(embed, '보낸 쪽')
        self.assertIn('213.209.159.84', sender)
        self.assertIn('curl/8.4.0', sender)

    def test_it_links_to_sentry(self):
        embed = self._payload({'event_id': 'abc123', 'exception': {'values': [{'type': 'OSError'}]}})
        link = self._field(embed, 'Sentry')
        self.assertIsNotNone(link, 'Sentry 링크가 없습니다')
        self.assertIn('abc123', link)

    def test_it_falls_back_to_culprit_when_there_is_no_transaction(self):
        embed = self._payload({
            'culprit': 'menu.views.menu_main',
            'exception': {'values': [{'type': 'OSError'}]},
        })
        self.assertEqual(self._field(embed, '위치'), 'menu.views.menu_main')

    def test_a_bare_event_does_not_crash_the_alert(self):
        """알림을 만들다 터지면 에러 기록 자체가 사라진다."""
        embed = self._payload({})
        self.assertEqual(self._field(embed, '요청'), '-')
        self.assertEqual(self._field(embed, '보낸 쪽'), '-')
