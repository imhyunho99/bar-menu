"""
입금 신청과 확인.

통장에는 입금자명만 찍힌다. 상호와 다른 경우가 대부분이라, 그 이름을
매장에 이어 붙일 근거가 화면 어딘가에 남아 있어야 나중에 '냈다/안 냈다'
가 갈릴 때 볼 것이 있다.
"""

from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from menu.models import PaymentRequest, Restaurant, Subscription


class ConfirmingAPaymentOpensTheStoreTests(TestCase):
    def setUp(self):
        self.restaurant = Restaurant.objects.create(name='미결제 바', slug='unpaid-bar')
        self.staff = User.objects.create_user('me@example.com', password='pw-12345678', is_staff=True)
        self.request = PaymentRequest.objects.create(
            restaurant=self.restaurant,
            plan='entry',
            depositor_name='홍길동',
            amount=9900,
        )

    def _subscription(self):
        return Restaurant.objects.get(slug='unpaid-bar').subscription

    def test_a_new_request_waits(self):
        self.assertEqual(self.request.status, 'pending')

    def test_confirming_turns_the_subscription_on(self):
        self.request.confirm(months=1, user=self.staff)

        subscription = self._subscription()
        self.assertEqual(subscription.status, 'active')
        self.assertTrue(subscription.is_usable())

    def test_confirming_records_who_and_when(self):
        self.request.confirm(months=1, user=self.staff)
        self.request.refresh_from_db()

        self.assertEqual(self.request.status, 'confirmed')
        self.assertEqual(self.request.confirmed_by, self.staff)
        self.assertIsNotNone(self.request.confirmed_at)

    def test_confirming_moves_the_store_to_the_plan_that_was_paid_for(self):
        """
        Premium 을 보내고 Entry 로 열리면 사장님은 낸 만큼 못 쓴다.
        요금제는 신청서가 정한다.
        """
        self.request.plan = 'premium'
        self.request.save(update_fields=['plan'])
        self.request.confirm(months=1, user=self.staff)

        self.assertEqual(self._subscription().plan, 'premium')

    def test_a_month_is_added_from_today_when_nothing_is_running(self):
        before = timezone.now()
        self.request.confirm(months=1, user=self.staff)

        until = self._subscription().access_until
        self.assertGreater(until, before + timedelta(days=27))
        self.assertLess(until, before + timedelta(days=33))

    def test_paying_early_does_not_eat_the_remaining_days(self):
        """
        만료 전에 미리 낸 사람의 남은 날을 먹으면 안 된다. 오늘부터 한 달이
        아니라 '기존 만료일부터' 한 달이다.
        """
        subscription = self.restaurant.subscription
        subscription.status = 'active'
        subscription.current_period_end = timezone.now() + timedelta(days=20)
        subscription.save(update_fields=['status', 'current_period_end'])

        self.request.confirm(months=1, user=self.staff)

        self.assertGreater(self._subscription().access_until, timezone.now() + timedelta(days=45))

    def test_an_expired_period_restarts_from_today(self):
        """기간이 이미 지났으면 과거에 더해 봐야 여전히 과거다."""
        subscription = self.restaurant.subscription
        subscription.status = 'active'
        subscription.current_period_end = timezone.now() - timedelta(days=40)
        subscription.save(update_fields=['status', 'current_period_end'])

        self.request.confirm(months=1, user=self.staff)

        self.assertTrue(self._subscription().is_usable())

    def test_three_months_is_three_months(self):
        self.request.confirm(months=3, user=self.staff)
        self.assertGreater(self._subscription().access_until, timezone.now() + timedelta(days=85))

    def test_confirming_twice_does_not_stack(self):
        """
        같은 신청을 두 번 눌러도 기간이 두 배가 되면 안 된다. 목록에서
        두 번 클릭하는 일은 실제로 일어난다.
        """
        self.request.confirm(months=1, user=self.staff)
        first = self._subscription().access_until

        self.request.confirm(months=1, user=self.staff)
        self.assertEqual(self._subscription().access_until, first)

    def test_a_partner_is_not_demoted_by_a_confirmation(self):
        """
        파트너는 영구 무제한이다. 입금 확인이 active 로 내리면 한 달 뒤
        영업 중인 가게가 꺼진다.
        """
        subscription = self.restaurant.subscription
        subscription.status = Subscription.UNLIMITED_STATUS
        subscription.save(update_fields=['status'])

        self.request.confirm(months=1, user=self.staff)

        self.assertEqual(self._subscription().status, Subscription.UNLIMITED_STATUS)
        self.assertTrue(self._subscription().is_usable())


class OwnerSubmitsAPaymentRequestTests(TestCase):
    def setUp(self):
        from menu.models import UserProfile

        self.restaurant = Restaurant.objects.create(name='미결제 바', slug='unpaid-bar')
        self.user = User.objects.create_user('owner@example.com', password='pw-12345678')
        UserProfile.objects.create(user=self.user, restaurant=self.restaurant)
        self.client.force_login(self.user)
        self.url = '/unpaid-bar/admin/billing/request/'

    def test_submitting_creates_a_pending_request(self):
        response = self.client.post(self.url, {'depositor_name': '홍길동', 'plan': 'entry'})
        self.assertEqual(response.status_code, 302)

        request = PaymentRequest.objects.get(restaurant=self.restaurant)
        self.assertEqual(request.depositor_name, '홍길동')
        self.assertEqual(request.amount, Subscription.PLAN_PRICES['entry'])
        self.assertEqual(request.status, 'pending')

    def test_the_amount_comes_from_the_server_not_the_form(self):
        """
        금액을 폼에서 받으면 사장님이 1원을 보내고 1원이라고 적을 수 있다.
        요금제만 받고 금액은 서버가 정한다.
        """
        self.client.post(self.url, {'depositor_name': '홍길동', 'plan': 'pro', 'amount': '1'})
        request = PaymentRequest.objects.get(restaurant=self.restaurant)
        self.assertEqual(request.amount, Subscription.PLAN_PRICES['pro'])

    def test_a_second_request_is_refused_while_one_is_waiting(self):
        """같은 입금이 두 줄로 남으면 통장과 대조할 때 헷갈린다."""
        payload = {'depositor_name': '홍길동', 'plan': 'entry'}
        self.client.post(self.url, payload)
        self.client.post(self.url, payload)

        self.assertEqual(PaymentRequest.objects.filter(restaurant=self.restaurant).count(), 1)

    def test_an_empty_depositor_name_is_refused(self):
        self.client.post(self.url, {'depositor_name': '   ', 'plan': 'entry'})
        self.assertEqual(PaymentRequest.objects.count(), 0)

    def test_an_unknown_plan_is_refused(self):
        self.client.post(self.url, {'depositor_name': '홍길동', 'plan': 'free-forever'})
        self.assertEqual(PaymentRequest.objects.count(), 0)

    def test_another_owner_cannot_submit_for_our_store(self):
        from menu.models import UserProfile

        intruder = User.objects.create_user('other@example.com', password='pw-12345678')
        other = Restaurant.objects.create(name='남의 바', slug='other-bar')
        UserProfile.objects.create(user=intruder, restaurant=other)
        self.client.force_login(intruder)

        response = self.client.post(self.url, {'depositor_name': '나쁜사람', 'plan': 'entry'})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(PaymentRequest.objects.count(), 0)

    def test_the_billing_page_shows_the_bank_account(self):
        with self.settings(BANK_NAME='국민', BANK_ACCOUNT='123-45-678', BANK_HOLDER='나현호'):
            response = self.client.get('/unpaid-bar/admin/billing/')
        self.assertContains(response, '123-45-678')

    def test_a_waiting_request_replaces_the_form(self):
        self.client.post(self.url, {'depositor_name': '홍길동', 'plan': 'entry'})
        with self.settings(BANK_NAME='국민', BANK_ACCOUNT='123-45-678', BANK_HOLDER='나현호'):
            response = self.client.get('/unpaid-bar/admin/billing/')
        self.assertContains(response, '확인 중입니다')
        self.assertContains(response, '홍길동')


class PaymentRequestNotificationTests(TestCase):
    def setUp(self):
        from menu.models import UserProfile

        self.restaurant = Restaurant.objects.create(name='미결제 바', slug='unpaid-bar')
        self.user = User.objects.create_user('owner@example.com', password='pw-12345678')
        UserProfile.objects.create(user=self.user, restaurant=self.restaurant, phone='010-1111-2222')
        self.request = PaymentRequest.objects.create(
            restaurant=self.restaurant, plan='entry',
            depositor_name='홍길동', amount=9900,
        )

    def test_payload_carries_what_we_need_to_match_the_bank_line(self):
        from menu.notifications import build_payment_request_payload

        text = str(build_payment_request_payload(self.request))

        self.assertIn('홍길동', text)
        self.assertIn('9,900', text)
        self.assertIn('unpaid-bar', text)
        self.assertIn('owner@example.com', text)
        self.assertIn('010-1111-2222', text)


class PaymentRequestAdminTests(TestCase):
    def setUp(self):
        from django.contrib.admin.sites import site

        self.site = site
        self.restaurant = Restaurant.objects.create(name='미결제 바', slug='unpaid-bar')
        self.staff = User.objects.create_superuser('me@example.com', password='pw-12345678')
        self.request = PaymentRequest.objects.create(
            restaurant=self.restaurant, plan='entry',
            depositor_name='홍길동', amount=9900,
        )

    def _admin(self):
        from menu.admin import PaymentRequestAdmin

        admin_instance = PaymentRequestAdmin(PaymentRequest, self.site)
        # message_user 는 메시지 프레임워크가 붙은 요청을 기대한다.
        # 액션이 하는 일만 보려는 테스트라 전달만 삼킨다.
        admin_instance.message_user = lambda *args, **kwargs: None
        return admin_instance

    def _http_request(self):
        from django.test import RequestFactory

        http_request = RequestFactory().post('/admin/')
        http_request.user = self.staff
        return http_request

    def test_subscription_is_reachable_from_admin(self):
        """
        알림을 받고 손으로 partner 로 바꾸거나 기간을 미루려면 admin 에
        있어야 한다. 지금까지 등록조차 되어 있지 않아 shell 을 열어야 했다.
        """
        self.assertIn(Subscription, self.site._registry)

    def test_payment_request_is_reachable_from_admin(self):
        self.assertIn(PaymentRequest, self.site._registry)

    def test_one_click_opens_the_store_for_a_month(self):
        self._admin().confirm_1(
            self._http_request(), PaymentRequest.objects.filter(pk=self.request.pk),
        )

        subscription = Restaurant.objects.get(slug='unpaid-bar').subscription
        self.assertEqual(subscription.status, 'active')
        self.assertTrue(subscription.is_usable())

    def test_the_year_action_opens_it_for_a_year(self):
        self._admin().confirm_12(
            self._http_request(), PaymentRequest.objects.filter(pk=self.request.pk),
        )

        subscription = Restaurant.objects.get(slug='unpaid-bar').subscription
        self.assertGreater(subscription.access_until, timezone.now() + timedelta(days=350))

    def test_confirming_several_at_once(self):
        second_store = Restaurant.objects.create(name='두번째 바', slug='second-bar')
        PaymentRequest.objects.create(
            restaurant=second_store, plan='entry', depositor_name='김철수', amount=9900,
        )

        self._admin().confirm_1(self._http_request(), PaymentRequest.objects.all())

        for slug in ('unpaid-bar', 'second-bar'):
            self.assertTrue(Restaurant.objects.get(slug=slug).subscription.is_usable(), slug)
