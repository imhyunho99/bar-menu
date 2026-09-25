"""
QR 발행은 입금 확인 뒤다.

예전에는 QR 이 게이트의 예외였다. '결제 전에도 QR 준비까지 된다' 고
안내했기 때문인데, 방침이 뒤집혔다. 그리고 이 뷰에는 로그인 검사조차
없어서 주소만 알면 아무나 남의 매장 QR 을 뽑을 수 있었다.
"""

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from menu.models import Restaurant, UserProfile


class QrNeedsPaymentTests(TestCase):
    def setUp(self):
        self.restaurant = Restaurant.objects.create(name='미결제 바', slug='unpaid-bar')
        self.user = User.objects.create_user('owner@example.com', password='pw-12345678')
        UserProfile.objects.create(user=self.user, restaurant=self.restaurant)

    def test_anonymous_visitor_cannot_reach_the_qr_page(self):
        response = self.client.get('/unpaid-bar/qr/')
        self.assertIn(response.status_code, (302, 403))

    def test_another_owner_cannot_print_our_qr(self):
        intruder = User.objects.create_user('other@example.com', password='pw-12345678')
        other_store = Restaurant.objects.create(name='남의 바', slug='other-bar')
        UserProfile.objects.create(user=intruder, restaurant=other_store)
        self.client.force_login(intruder)

        response = self.client.get('/unpaid-bar/qr/')
        self.assertEqual(response.status_code, 403)

    @override_settings(ENFORCE_SUBSCRIPTION=True)
    def test_unpaid_owner_sees_how_to_pay_instead_of_a_qr(self):
        self.client.force_login(self.user)
        response = self.client.get('/unpaid-bar/qr/')

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'menu/qr_locked.html')
        self.assertNotContains(response, 'data:image/png;base64')

    @override_settings(ENFORCE_SUBSCRIPTION=True)
    def test_the_locked_screen_points_at_how_to_open_it(self):
        """
        막다른 길로 끝내면 사장님은 관리 화면을 닫고 다시 오지 않는다.
        무엇을 하면 열리는지가 같은 화면에 있어야 한다.
        """
        self.client.force_login(self.user)
        response = self.client.get('/unpaid-bar/qr/')
        self.assertContains(response, '/unpaid-bar/admin/billing/')

    @override_settings(ENFORCE_SUBSCRIPTION=True)
    def test_paid_owner_gets_the_qr(self):
        subscription = self.restaurant.subscription
        subscription.status = 'partner'
        subscription.save(update_fields=['status'])

        self.client.force_login(self.user)
        response = self.client.get('/unpaid-bar/qr/')

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'menu/qr_code.html')

    @override_settings(ENFORCE_SUBSCRIPTION=False)
    def test_the_gate_being_off_does_not_lock_the_qr(self):
        """
        게이트가 꺼져 있으면 미결제 매장의 메뉴판도 실제로 열려 있다.
        그때 QR 만 막으면, 열려 있는 메뉴판을 가리키는 QR 을 못 뽑는
        앞뒤가 안 맞는 상태가 된다. menu_is_live 가 둘을 함께 움직인다.
        """
        self.client.force_login(self.user)
        response = self.client.get('/unpaid-bar/qr/')
        self.assertTemplateUsed(response, 'menu/qr_code.html')


@override_settings(CUSTOMER_SITE_URL='https://bar-menu.ddnsfree.com')
class ThePrintedQRPointsAtTheCustomerSiteTests(TestCase):
    """
    인쇄된 QR 은 고칠 수 없다. 여기가 틀리면 손님이 종이를 찍고 404 를 본다.

    사장님은 Django admin(api.*)에서 이 화면에 들어온다. 요청 호스트로 주소를
    만들면 api.* 가 박히는데, QR 전용 진입점 `/<slug>/enter/` 는 Next.js 쪽에만
    있는 경로다. 2026-09-25 검토에서 실제로 그 상태였다 —
    `https://api.bar-menu.ddnsfree.com/bid/enter/` 는 404 를 준다.

    API 쪽(`menu/api/views.py:_qr_base_url`)은 같은 이유로 이미 고쳐져 있었다.
    규칙이 두 군데로 갈려서 사장님이 실제로 인쇄하는 쪽만 남아 있었다.
    """

    def setUp(self):
        self.restaurant = Restaurant.objects.create(name='달빛', slug='moonlight')
        subscription = self.restaurant.subscription
        subscription.status = 'partner'
        subscription.save(update_fields=['status'])
        self.user = User.objects.create_superuser('boss', 'b@x.test', 'pw-2591')
        self.client.force_login(self.user)

    def _menu_url(self):
        response = self.client.get('/moonlight/qr/')
        self.assertEqual(response.status_code, 200)
        return response.context['menu_url']

    def test_it_uses_the_customer_site_not_the_admin_host(self):
        url = self._menu_url()
        self.assertTrue(url.startswith('https://bar-menu.ddnsfree.com/'), url)
        self.assertNotIn('testserver', url)

    def test_it_keeps_the_qr_only_entrance(self):
        """/enter/ 로 들어와야 QR 전용 화면이 뜬다."""
        self.assertEqual(self._menu_url(), 'https://bar-menu.ddnsfree.com/moonlight/enter/')

    @override_settings(CUSTOMER_SITE_URL='')
    def test_without_the_setting_it_falls_back_instead_of_dying(self):
        """주소를 모르면 예전처럼 요청 호스트로 떨어진다. 화면이 죽는 것보다 낫다."""
        self.assertIn('/moonlight/enter/', self._menu_url())
