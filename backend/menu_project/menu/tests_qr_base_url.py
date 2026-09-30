"""
QR 이 가리키는 주소를 누가 정하는가.

예전에는 ?base_url= 을 그대로 믿었다. 아무나 남의 도메인을 넣어 QR 을
받을 수 있었고, 그 QR 에는 매장 로고까지 박혔다 — 우리 도메인이 발급한
진짜처럼 보이는 피싱용 QR 을 우리 API 가 만들어 준 셈이다.

이제 아는 주소만 받는다. 모르는 값이 오면 거절하는 대신 조용히 우리
주소로 바꾼다 — QR 을 보러 온 사장님에게 에러를 띄울 이유가 없고,
공격자에게는 아무것도 안 준다.
"""

from django.test import TestCase, override_settings

from menu.models import Restaurant


@override_settings(
    ENFORCE_SUBSCRIPTION=False,
    CUSTOMER_SITE_URL='https://develop.example.com',
)
class QrBaseUrlTests(TestCase):
    def setUp(self):
        self.restaurant = Restaurant.objects.create(name='큐알 바', slug='qr-bar')
        self.url = '/api/v1/restaurants/qr-bar/qr/'

    def _menu_url(self, query=''):
        return self.client.get(self.url + query).json()['menu_url']

    def test_a_foreign_base_url_is_not_honored(self):
        got = self._menu_url('?base_url=https://evil.example.test')
        self.assertNotIn('evil.example.test', got)

    def test_a_lookalike_domain_is_not_honored(self):
        """
        접두사만 맞춰도 통과하면 develop.example.com.evil.test 가 뚫린다.
        """
        got = self._menu_url('?base_url=https://develop.example.com.evil.test')
        self.assertNotIn('evil.test', got)

    def test_the_configured_customer_site_is_honored(self):
        got = self._menu_url('?base_url=https://develop.example.com')
        self.assertEqual(got, 'https://develop.example.com/qr-bar/enter/')

    def test_a_trailing_slash_is_honored(self):
        got = self._menu_url('?base_url=https://develop.example.com/')
        self.assertEqual(got, 'https://develop.example.com/qr-bar/enter/')

    def test_no_base_url_falls_back_to_the_customer_site(self):
        """
        손님이 실제로 보는 화면은 Next.js 다. 요청 호스트(api.*)로 만들면
        Django 가 그리는 다른 화면을 가리키는 QR 이 인쇄된다.
        """
        self.assertEqual(self._menu_url(), 'https://develop.example.com/qr-bar/enter/')

    @override_settings(CUSTOMER_SITE_URL='')
    def test_without_a_configured_site_it_uses_the_request_host(self):
        """설정이 없으면 예전처럼 요청 호스트로 떨어진다. 남의 도메인은 여전히 아니다."""
        got = self._menu_url('?base_url=https://evil.example.test')
        self.assertNotIn('evil.example.test', got)
        self.assertIn('/qr-bar/enter/', got)
