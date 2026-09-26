"""
가입 폭주를 막는가.

/signup/ 은 로그인 없이 누구나 POST 할 수 있고, 한 번에 staff 계정·매장·구독을
만들고 Discord 로 알림을 쏜다. 2026-09-25 적대적 검토가 지적했다 — 스크립트
하나로 계정과 slug 가 무한정 생기고, 알림 채널이 묻혀 **진짜 에러 알림이
안 보인다**.

나머지 테스트는 같은 프로세스에서 127.0.0.1 로 19번 가입하므로 캐시를 더미로
둔다(settings). 여기서만 진짜 캐시를 켜고 확인한다.
"""

from unittest import mock

from django.core.cache import cache
from django.test import TestCase, override_settings

from menu.models import Restaurant

LOCMEM = {'default': {
    'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    'LOCATION': 'signup-rate-limit-test',
}}


@override_settings(CACHES=LOCMEM, SIGNUP_MAX_PER_HOUR=3)
@mock.patch('menu.onboarding_views.notifications.send_signup_notification', return_value=True)
class SignupIsRateLimitedTests(TestCase):
    def setUp(self):
        cache.clear()

    def _signup(self, n):
        return self.client.post('/signup/', {
            'email': f'owner{n}@example.com',
            'password': 'jazz-bar-9137',
            'name': f'가게 {n}',
            'slug': f'shop-{n}',
        })

    def test_the_first_few_go_through(self, _notify):
        for n in range(3):
            with self.subTest(n=n):
                self.assertEqual(self._signup(n).status_code, 302)
        self.assertEqual(Restaurant.objects.count(), 3)

    def test_the_next_one_is_refused(self, _notify):
        for n in range(3):
            self._signup(n)
        response = self._signup(99)

        self.assertEqual(response.status_code, 200, '가입이 됐습니다')
        self.assertFalse(Restaurant.objects.filter(slug='shop-99').exists())
        self.assertIn('너무 잦습니다', response.content.decode('utf-8'))

    def test_a_refused_attempt_does_not_notify(self, notify):
        """알림 채널이 묻히는 것이 피해의 절반이다."""
        for n in range(3):
            self._signup(n)
        notify.reset_mock()
        self._signup(99)
        notify.assert_not_called()

    def test_another_shop_on_another_network_is_not_punished(self, _notify):
        """한 사람이 많이 눌렀다고 옆 가게 가입이 막히면 안 된다."""
        for n in range(4):
            self._signup(n)
        response = self.client.post('/signup/', {
            'email': 'other@example.com',
            'password': 'jazz-bar-9137',
            'name': '다른 가게',
            'slug': 'other-shop',
        }, HTTP_X_FORWARDED_FOR='203.0.113.9')

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Restaurant.objects.filter(slug='other-shop').exists())

    def test_the_limit_can_be_turned_off(self, _notify):
        """운영에서 급할 때 끌 수 있어야 한다. 0 이면 제한 없음."""
        with override_settings(SIGNUP_MAX_PER_HOUR=0):
            for n in range(6):
                self.assertEqual(self._signup(n).status_code, 302)
