"""
결제 복귀 처리와 정기청구.

카카오페이는 승인이 '돌아오는 길'에 일어나고, 다음 달 청구를 대신 해 주지
않는다. 그래서 두 가지가 우리 몫이다 — 복귀 뷰와 스케줄러. 여기서 지키려는
것은 하나다: 돈이 오가는 지점에서 '성공한 척'이 생기지 않게 한다.
"""

from datetime import timedelta
from io import StringIO
from unittest import mock

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from .billing import base
from .billing.kakaopay import KakaoPayProvider
from .models import Restaurant, Subscription, UserProfile

CONF = dict(PAYMENT_PROVIDER='kakaopay', KAKAOPAY_SECRET_KEY='DEV', KAKAOPAY_CID='TCSUBSCRIP')


@override_settings(**CONF)
class ApproveReturnViewTests(TestCase):
    def setUp(self):
        self.restaurant = Restaurant.objects.create(name='달빛 이자카야', slug='moonlight')
        self.sub = self.restaurant.subscription
        self.sub.pending_tid = 'T555'
        # 결제 경로는 체험이 끝난 뒤의 이야기다. 출발점을 미결제로 못박지 않으면
        # '결제에 실패했는데도 활성화됐는가' 를 확인할 수 없다.
        self.sub.status = 'unpaid'
        self.sub.current_period_end = None
        self.sub.save()
        self.owner = User.objects.create_user('owner', password='pw', is_staff=True)
        UserProfile.objects.create(user=self.owner, restaurant=self.restaurant)
        self.client.force_login(self.owner)
        self.url = '/moonlight/admin/billing/approve/'

    def _ok_event(self):
        return base.BillingEvent(
            kind=base.EVENT_PAYMENT_SUCCEEDED,
            provider_subscription_id='S-ABC',
            period_end=timezone.now() + timedelta(days=30),
        )

    def test_successful_return_activates_the_subscription(self):
        with mock.patch.object(KakaoPayProvider, 'approve_return', return_value=self._ok_event()):
            r = self.client.get(self.url, {'result': 'approve', 'pg_token': 'PG1'}, follow=True)
        self.assertEqual(r.status_code, 200)
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.status, 'active')
        self.assertIsNotNone(self.sub.current_period_end)

    def test_successful_return_opens_the_customer_screen(self):
        """결제의 목적은 손님 화면을 여는 것이다. 거기까지 확인한다."""
        with mock.patch.object(KakaoPayProvider, 'approve_return', return_value=self._ok_event()):
            self.client.get(self.url, {'result': 'approve', 'pg_token': 'PG1'}, follow=True)
        self.sub.refresh_from_db()
        self.assertTrue(self.sub.is_usable())

    def test_cancelled_return_leaves_it_unpaid(self):
        """사용자가 결제창을 닫고 돌아온 경우."""
        with mock.patch.object(KakaoPayProvider, 'approve_return') as ap:
            r = self.client.get(self.url, {'result': 'cancel'}, follow=True)
            ap.assert_not_called()
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.status, 'unpaid')
        self.assertContains(r, '결제가 취소')

    def test_failed_return_leaves_it_unpaid(self):
        with mock.patch.object(KakaoPayProvider, 'approve_return') as ap:
            self.client.get(self.url, {'result': 'fail'}, follow=True)
            ap.assert_not_called()
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.status, 'unpaid')

    def test_approval_error_does_not_activate(self):
        """승인이 실패했는데 활성화되면 공짜로 열린다."""
        with mock.patch.object(KakaoPayProvider, 'approve_return',
                               side_effect=base.PaymentError('승인 거절')):
            r = self.client.get(self.url, {'result': 'approve', 'pg_token': 'PG1'}, follow=True)
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.status, 'unpaid')
        self.assertFalse(self.sub.is_usable())

    def test_other_tenant_cannot_approve_my_subscription(self):
        other = Restaurant.objects.create(name='남의 가게', slug='other')
        u = User.objects.create_user('u2', password='pw', is_staff=True)
        UserProfile.objects.create(user=u, restaurant=other)
        self.client.force_login(u)
        with mock.patch.object(KakaoPayProvider, 'approve_return') as ap:
            r = self.client.get(self.url, {'result': 'approve', 'pg_token': 'PG1'})
            ap.assert_not_called()
        self.assertEqual(r.status_code, 403)


@override_settings(**CONF)
class RecurringChargeCommandTests(TestCase):
    """
    카카오페이는 다음 달에 알아서 청구해 주지 않는다.
    이 명령이 없으면 모든 구독이 한 달 뒤 조용히 만료된다.
    """

    def _sub(self, slug, **kw):
        r = Restaurant.objects.create(name=slug, slug=slug)
        s = r.subscription
        s.status = kw.get('status', 'active')
        s.plan = 'pro'
        s.provider = 'kakaopay'
        s.provider_subscription_id = kw.get('sid', f'S-{slug}')
        s.current_period_end = kw.get('end')
        s.save()
        return s

    def _ok(self, sub):
        return base.BillingEvent(kind=base.EVENT_PAYMENT_SUCCEEDED,
                                 provider_subscription_id=sub.provider_subscription_id,
                                 period_end=timezone.now() + timedelta(days=30))

    def test_expired_subscription_is_charged_and_extended(self):
        s = self._sub('due', end=timezone.now() - timedelta(hours=1))
        with mock.patch.object(KakaoPayProvider, 'charge', side_effect=lambda sub, **k: self._ok(sub)) as ch:
            call_command('charge_subscriptions', stdout=StringIO())
            ch.assert_called_once()
        s.refresh_from_db()
        self.assertEqual(s.status, 'active')
        self.assertGreater(s.current_period_end, timezone.now())

    def test_subscription_not_yet_due_is_left_alone(self):
        self._sub('later', end=timezone.now() + timedelta(days=10))
        with mock.patch.object(KakaoPayProvider, 'charge') as ch:
            call_command('charge_subscriptions', stdout=StringIO())
            ch.assert_not_called()

    def test_canceled_subscription_is_not_charged(self):
        """해지한 사장님에게 청구하면 그건 사고다."""
        self._sub('gone', status='canceled', end=timezone.now() - timedelta(days=1))
        with mock.patch.object(KakaoPayProvider, 'charge') as ch:
            call_command('charge_subscriptions', stdout=StringIO())
            ch.assert_not_called()

    def test_failed_charge_becomes_past_due_not_closed(self):
        """카드 한 번 실패했다고 영업 중인 가게 메뉴판을 끄지 않는다."""
        s = self._sub('fail', end=timezone.now() - timedelta(hours=1))
        ev = base.BillingEvent(kind=base.EVENT_PAYMENT_FAILED,
                               provider_subscription_id=s.provider_subscription_id)
        with mock.patch.object(KakaoPayProvider, 'charge', return_value=ev):
            call_command('charge_subscriptions', stdout=StringIO())
        s.refresh_from_db()
        self.assertEqual(s.status, 'past_due')
        self.assertTrue(s.is_usable())

    def test_dry_run_charges_nobody(self):
        self._sub('due', end=timezone.now() - timedelta(hours=1))
        with mock.patch.object(KakaoPayProvider, 'charge') as ch:
            call_command('charge_subscriptions', '--dry-run', stdout=StringIO())
            ch.assert_not_called()

    def test_partner_subscription_is_never_charged(self):
        """무제한 파트너에게 청구하면 안 된다."""
        self._sub('partner', status='partner', end=timezone.now() - timedelta(days=1))
        with mock.patch.object(KakaoPayProvider, 'charge') as ch:
            call_command('charge_subscriptions', stdout=StringIO())
            ch.assert_not_called()

    def test_missing_key_stops_instead_of_marking_everyone_past_due(self):
        """
        운영에서 키가 빠졌을 때.

        설정이 없는 걸 '결제 실패'로 취급하면 멀쩡히 결제되던 매장이 전부
        past_due 가 된다. 우리 설정 사고를 사장님 카드 탓으로 돌리는 셈이다.
        그런 경우엔 아무도 건드리지 말고 멈춰야 한다.
        """
        s = self._sub('due', end=timezone.now() - timedelta(hours=1))
        err = StringIO()
        with override_settings(KAKAOPAY_SECRET_KEY='', KAKAOPAY_CID=''):
            call_command('charge_subscriptions', stdout=StringIO(), stderr=err)
        s.refresh_from_db()
        self.assertEqual(s.status, 'active', '설정 사고로 상태를 바꾸면 안 된다')
        self.assertIn('중단', err.getvalue())
