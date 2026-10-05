"""
공개 API 가 내보내면 안 되는 값을 내보내는가.

2026-10-05 실측에서 나왔다. 운영 API 를 그냥 curl 하면 이런 게 따라 나왔다.

    site_settings.wifi_password  = '...'       ← enable_wifi 는 False 였다
    site_settings.store_public_ip = '...'      ← restrict_by_ip 는 False 였다

화면이 안 쓰는 것과 API 가 안 주는 것은 다른 문제다. 손님 화면은 와이파이가
꺼져 있으면 비밀번호를 안 그리지만, API 는 끈 매장의 비밀번호까지 그대로
줬다. 매장 공인 IP 도 마찬가지다 — 그건 손님에게 보여줄 값이 아니라
'매장 안에서만 열람'을 판정하려고 두는 값이다.

여기서 고정하는 계약: **끈 기능의 값은 응답에 없다.**

아직 안 한 것: IP 게이트 판정 자체는 여전히 Next.js 에만 있다. API 를 직접
부르면 게이트와 상관없이 메뉴가 나온다. 그건 구조 변경이라 따로 다룬다 —
이 테스트는 "값이 새지 않는다"까지만 지킨다.
"""

from django.test import TestCase

from menu.models import Restaurant, SiteSettings


class DisabledFeaturesLeaveNothingInTheResponseTests(TestCase):
    def setUp(self):
        self.restaurant = Restaurant.objects.create(name='샘', slug='leak-bar')
        # 구독 게이트를 통과시킨다. 안 하면 402 가 와서 무엇을 재는지 알 수 없다.
        self.restaurant.subscription.status = 'partner'
        self.restaurant.subscription.save(update_fields=['status'])
        self.settings = SiteSettings.objects.get_or_create(restaurant=self.restaurant)[0]
        self.url = '/api/v1/restaurants/leak-bar/'

    def _settings_payload(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        return response.json().get('site_settings') or {}

    def _configure(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self.settings, key, value)
        self.settings.save()

    # ─── 와이파이 ───────────────────────────────────────────

    def test_wifi_credentials_are_absent_when_the_feature_is_off(self):
        self._configure(
            enable_wifi=False,
            wifi_ssid='BidbaR_2G',
            wifi_password='super-secret',
        )
        payload = self._settings_payload()
        self.assertNotIn('wifi_password', payload, '와이파이를 껐는데 비밀번호가 나갑니다')
        self.assertNotIn('wifi_ssid', payload)
        self.assertNotIn('wifi_security', payload)

    def test_wifi_credentials_are_present_when_the_feature_is_on(self):
        """꺼진 것만 숨긴다. 켠 매장은 손님 화면이 실제로 이 값을 쓴다."""
        self._configure(
            enable_wifi=True,
            wifi_ssid='BidbaR_2G',
            wifi_password='super-secret',
        )
        payload = self._settings_payload()
        self.assertEqual(payload.get('wifi_ssid'), 'BidbaR_2G')
        self.assertEqual(payload.get('wifi_password'), 'super-secret')

    # ─── 매장 공인 IP ───────────────────────────────────────

    def test_store_public_ip_is_absent_when_the_gate_is_off(self):
        self._configure(restrict_by_ip=False, store_public_ip='119.193.34.23')
        payload = self._settings_payload()
        self.assertNotIn(
            'store_public_ip', payload,
            '게이트를 껐는데 매장 공인 IP 가 나갑니다 — 손님에게 보여줄 값이 아닙니다',
        )

    def test_store_public_ip_is_present_when_the_gate_is_on(self):
        """
        게이트를 켠 매장은 손님 화면(서버 렌더)이 이 값으로 판정한다.
        브라우저까지 가지 않도록 Next.js 가 응답 직전에 지운다.
        """
        self._configure(restrict_by_ip=True, store_public_ip='119.193.34.23')
        payload = self._settings_payload()
        self.assertEqual(payload.get('store_public_ip'), '119.193.34.23')

    # ─── 포스 연동 ─────────────────────────────────────────

    def test_payhere_store_id_is_absent_when_the_integration_is_off(self):
        self._configure(enable_payhere=False, payhere_store_id='STORE-12345')
        payload = self._settings_payload()
        self.assertNotIn('payhere_store_id', payload)

    # ─── 그 외 ────────────────────────────────────────────

    def test_design_values_still_come_through(self):
        """
        숨기는 건 끈 기능의 값뿐이다. 디자인 값까지 빠지면 손님 화면이
        기본 테마로 떨어진다 — 조용히 매장 분위기가 사라진다.
        """
        self._configure(background_color='#101014', enable_wifi=False)
        payload = self._settings_payload()
        self.assertEqual(payload.get('background_color'), '#101014')
        self.assertIn('menu_name_color', payload)
