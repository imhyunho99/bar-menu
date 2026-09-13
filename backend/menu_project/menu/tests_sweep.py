"""
만료 스윕.

손님 화면이 닫히는 건 이 명령과 무관하다 — is_usable 이 실시간으로 날짜를
본다. 이 명령이 하는 일은 상태를 unpaid 로 내려 목록에서 '끝났다' 고 읽히게
하는 것과, 연장을 안내할 수 있도록 우리에게 알리는 것이다.
"""

from datetime import timedelta
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from menu.models import Restaurant


class SweepSubscriptionsTests(TestCase):
    def _store(self, slug, status, days):
        restaurant = Restaurant.objects.create(name=slug, slug=slug)
        subscription = restaurant.subscription
        subscription.status = status
        subscription.current_period_end = (
            timezone.now() + timedelta(days=days) if days is not None else None
        )
        subscription.save()
        return subscription

    def test_a_lapsed_paid_store_becomes_unpaid(self):
        subscription = self._store('lapsed', 'active', -1)
        call_command('sweep_subscriptions')
        subscription.refresh_from_db()
        self.assertEqual(subscription.status, 'unpaid')

    def test_a_running_store_is_left_alone(self):
        subscription = self._store('running', 'active', 10)
        call_command('sweep_subscriptions')
        subscription.refresh_from_db()
        self.assertEqual(subscription.status, 'active')

    def test_partner_is_never_touched(self):
        """파트너는 날짜를 보지 않는다. 옛 날짜가 붙어 있어도 건드리면 안 된다."""
        subscription = self._store('partner-store', 'partner', -400)
        call_command('sweep_subscriptions')
        subscription.refresh_from_db()
        self.assertEqual(subscription.status, 'partner')

    def test_a_never_opened_store_is_not_reported_as_expired(self):
        """
        한 번도 연 적 없는 무료 매장은 만료된 것이 아니다. 여기 섞이면
        가입만 하고 둘러보는 사장님마다 '끝났습니다' 알림이 온다.
        """
        subscription = self._store('free', 'unpaid', None)
        with patch('menu.notifications.send_subscription_expired_notification') as notify:
            call_command('sweep_subscriptions')
        notify.assert_not_called()
        subscription.refresh_from_db()
        self.assertEqual(subscription.status, 'unpaid')

    def test_a_lapsed_store_is_reported_once(self):
        self._store('lapsed', 'active', -1)
        with patch('menu.notifications.send_subscription_expired_notification') as notify:
            call_command('sweep_subscriptions')
            call_command('sweep_subscriptions')
        # 첫 스윕이 unpaid 로 내려서 두 번째 스윕의 대상에서 빠진다.
        self.assertEqual(notify.call_count, 1)

    def test_a_store_about_to_expire_is_warned(self):
        self._store('soon', 'active', 6)
        with patch('menu.notifications.send_expiring_soon_notification') as notify:
            call_command('sweep_subscriptions')
        notify.assert_called_once()

    def test_a_store_with_plenty_of_time_is_not_warned(self):
        self._store('later', 'active', 20)
        with patch('menu.notifications.send_expiring_soon_notification') as notify:
            call_command('sweep_subscriptions')
        notify.assert_not_called()

    def test_dry_run_changes_nothing(self):
        subscription = self._store('lapsed', 'active', -1)
        with patch('menu.notifications.send_subscription_expired_notification') as notify:
            call_command('sweep_subscriptions', '--dry-run')
        notify.assert_not_called()
        subscription.refresh_from_db()
        self.assertEqual(subscription.status, 'active')
