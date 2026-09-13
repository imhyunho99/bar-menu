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
