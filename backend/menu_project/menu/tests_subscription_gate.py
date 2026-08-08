"""
구독 게이트 미들웨어.

가장 중요한 성질은 '켜지 않으면 아무것도 막지 않는다' 이다. 결제 대행사가
붙기 전에 이게 켜지면, 체험이 끝난 사장님은 돈 낼 방법도 없이 손님 화면만
꺼진다. 그래서 기본 꺼짐과, 켜졌을 때도 사장님 경로는 열려 있음을 못박는다.
"""

from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone

from .models import Restaurant, Subscription


class SubscriptionGateTests(TestCase):
    def setUp(self):
        self.restaurant = Restaurant.objects.create(name="달빛 이자카야", slug="moonlight")
        self.menu_url = f"/{self.restaurant.slug}/"

    def _subscribe(self, **kwargs):
        return Subscription.objects.create(restaurant=self.restaurant, **kwargs)

    # ── 기본값: 꺼져 있다 ──────────────────────────────────────────
    def test_expired_store_stays_open_while_enforcement_is_off(self):
        self._subscribe(status='canceled', trial_ends_at=timezone.now() - timedelta(days=1))
        self.assertNotEqual(self.client.get(self.menu_url).status_code, 402)

    # ── 켰을 때 ────────────────────────────────────────────────────
    @override_settings(ENFORCE_SUBSCRIPTION=True)
    def test_canceled_store_is_closed_to_customers(self):
        self._subscribe(status='canceled')
        response = self.client.get(self.menu_url)
        self.assertEqual(response.status_code, 402)
        self.assertIn('메뉴판을 열 수 없습니다', response.content.decode())

    @override_settings(ENFORCE_SUBSCRIPTION=True)
    def test_expired_trial_is_closed_to_customers(self):
        self._subscribe(status='trialing', trial_ends_at=timezone.now() - timedelta(minutes=1))
        self.assertEqual(self.client.get(self.menu_url).status_code, 402)

    @override_settings(ENFORCE_SUBSCRIPTION=True)
    def test_trial_in_progress_is_open(self):
        self._subscribe(status='trialing', trial_ends_at=timezone.now() + timedelta(days=3))
        self.assertNotEqual(self.client.get(self.menu_url).status_code, 402)

    @override_settings(ENFORCE_SUBSCRIPTION=True)
    def test_payment_failure_does_not_close_a_trading_store(self):
        """카드 한 번 실패했다고 영업 중인 가게의 메뉴판을 끄면 그게 더 큰 사고다."""
        self._subscribe(status='past_due', current_period_end=timezone.now() - timedelta(days=2))
        self.assertNotEqual(self.client.get(self.menu_url).status_code, 402)

    @override_settings(ENFORCE_SUBSCRIPTION=True)
    def test_owner_can_still_reach_admin_to_pay(self):
        """되살리러 들어오는 문까지 잠그면 방법이 없어진다."""
        self._subscribe(status='canceled')
        User.objects.create_user('owner', password='pw', is_staff=True, is_superuser=True)
        self.client.login(username='owner', password='pw')

        response = self.client.get(f"/{self.restaurant.slug}/admin/dashboard/")
        self.assertEqual(response.status_code, 200)

    @override_settings(ENFORCE_SUBSCRIPTION=True)
    def test_store_without_a_subscription_row_is_untouched(self):
        """셀프가입 이전에 손으로 만든 매장을 소급해서 끌 이유가 없다."""
        self.assertNotEqual(self.client.get(self.menu_url).status_code, 402)


class SubscriptionModelTests(TestCase):
    def setUp(self):
        self.restaurant = Restaurant.objects.create(name="소록", slug="sorok-test")

    def test_start_trial_sets_status_and_deadline(self):
        sub = Subscription(restaurant=self.restaurant)
        sub.start_trial()
        sub.save()

        self.assertEqual(sub.status, 'trialing')
        self.assertTrue(sub.is_usable())
        # 14일에서 하루 이내 오차 (days 는 내림)
        self.assertIn(sub.days_left, (Subscription.TRIAL_DAYS - 1, Subscription.TRIAL_DAYS))

    def test_paid_period_takes_precedence_over_trial_end(self):
        sub = Subscription.objects.create(
            restaurant=self.restaurant,
            status='active',
            trial_ends_at=timezone.now() - timedelta(days=5),
            current_period_end=timezone.now() + timedelta(days=25),
        )
        self.assertTrue(sub.is_usable())
        self.assertEqual(sub.access_until, sub.current_period_end)

    def test_days_left_is_none_when_nothing_is_scheduled(self):
        sub = Subscription.objects.create(restaurant=self.restaurant, status='active')
        self.assertIsNone(sub.days_left)
        self.assertTrue(sub.is_usable())
