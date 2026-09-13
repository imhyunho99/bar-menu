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
