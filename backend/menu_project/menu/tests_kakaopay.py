"""
카카오페이 어댑터.

카카오페이는 웹훅을 주지 않는다. 흐름이 이렇다.
  ready  → 결제창 URL 과 tid 를 받아 사용자를 보낸다
  (사용자가 카카오톡에서 승인)
  복귀   → approval_url 로 pg_token 을 들고 돌아온다
  approve→ tid + pg_token 으로 승인하고 SID 를 받는다
  2회차~ → 저장한 SID 로 우리가 직접 청구한다

그래서 '대행사가 알려준다'가 아니라 '우리가 물어본다'가 된다. 이 차이가
테스트에서 확인해야 할 핵심이다 — 특히 마지막 줄: 카카오페이는 다음 달에
알아서 청구해 주지 않는다.
"""

import json
from datetime import timedelta
from unittest import mock

from django.test import TestCase, override_settings
from django.utils import timezone

from .billing import base
from .billing.kakaopay import KakaoPayProvider
from .models import Restaurant, Subscription

SECRET = 'DEV_SECRET_KEY_TEST'


def fake_response(payload):
    """어댑터의 _post 가 돌려주는 모양(파싱된 dict)."""
    return payload


@override_settings(KAKAOPAY_SECRET_KEY=SECRET, KAKAOPAY_CID='TCSUBSCRIP')
class KakaoPayCheckoutTests(TestCase):
    def setUp(self):
        self.restaurant = Restaurant.objects.create(name='달빛 이자카야', slug='moonlight')
        self.sub = self.restaurant.subscription
        self.p = KakaoPayProvider()

    def test_ready_sends_the_documented_payload(self):
        """문서에 있는 필수 파라미터를 빠뜨리면 카카오페이가 400 을 준다."""
        with mock.patch.object(KakaoPayProvider, '_post') as post:
            post.return_value = fake_response({
                'tid': 'T1234567890', 'next_redirect_pc_url': 'https://kakao.test/pay',
                'created_at': '2026-08-19T10:00:00',
            })
            url = self.p.start_checkout(self.sub, 'pro', 'https://bar-menu.test/back')

        path, body = post.call_args[0][0], post.call_args[0][1]
        self.assertEqual(path, '/online/v1/payment/ready')
        for key in ('cid', 'partner_order_id', 'partner_user_id', 'item_name',
                    'quantity', 'total_amount', 'tax_free_amount',
                    'approval_url', 'cancel_url', 'fail_url'):
            self.assertIn(key, body, f'{key} 가 빠지면 ready 가 실패한다')
        self.assertEqual(body['cid'], 'TCSUBSCRIP')
        self.assertEqual(body['total_amount'], Subscription.PLAN_PRICES['pro'])
        self.assertEqual(url, 'https://kakao.test/pay')

    def test_ready_stores_tid_for_the_return_trip(self):
        """복귀 시 pg_token 만으로는 승인할 수 없다. tid 를 들고 있어야 한다."""
        with mock.patch.object(KakaoPayProvider, '_post') as post:
            post.return_value = fake_response({'tid': 'T999', 'next_redirect_pc_url': 'https://k/'})
            self.p.start_checkout(self.sub, 'entry', 'https://bar-menu.test/back')
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.pending_tid, 'T999')

    def test_ready_does_not_activate_the_subscription(self):
        """결제창을 띄운 것과 결제된 것은 다르다. 창을 닫고 나간 사장님이 공짜로 쓰면 안 된다."""
        with mock.patch.object(KakaoPayProvider, '_post') as post:
            post.return_value = fake_response({'tid': 'T1', 'next_redirect_pc_url': 'https://k/'})
            self.p.start_checkout(self.sub, 'pro', 'https://bar-menu.test/back')
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.status, 'unpaid')

    def test_partner_user_id_carries_no_personal_data(self):
        """문서 명시: 실명·휴대폰번호·이메일·ID 전송 불가."""
        with mock.patch.object(KakaoPayProvider, '_post') as post:
            post.return_value = fake_response({'tid': 'T1', 'next_redirect_pc_url': 'https://k/'})
            self.p.start_checkout(self.sub, 'pro', 'https://bar-menu.test/back')
        uid = post.call_args[0][1]['partner_user_id']
        self.assertNotIn('@', uid)
        self.assertIn(str(self.restaurant.id), uid)


@override_settings(KAKAOPAY_SECRET_KEY=SECRET, KAKAOPAY_CID='TCSUBSCRIP')
class KakaoPayApproveTests(TestCase):
    def setUp(self):
        self.restaurant = Restaurant.objects.create(name='달빛 이자카야', slug='moonlight')
        self.sub = self.restaurant.subscription
        self.sub.pending_tid = 'T555'
        self.sub.save()
        self.p = KakaoPayProvider()

    def _approved(self, **over):
        d = {'aid': 'A1', 'tid': 'T555', 'cid': 'TCSUBSCRIP', 'sid': 'S-ABC',
             'partner_order_id': 'o1', 'partner_user_id': 'u1',
             'payment_method_type': 'CARD',
             'amount': {'total': 19900, 'tax_free': 0, 'vat': 1809},
             'item_name': 'Pro', 'quantity': 1,
             'approved_at': '2026-08-19T10:05:00'}
        d.update(over)
        return d

    def test_approve_stores_sid_and_activates(self):
        with mock.patch.object(KakaoPayProvider, '_post') as post:
            post.return_value = fake_response(self._approved())
            ev = self.p.approve_return(self.sub, {'pg_token': 'PG1'})

        path, body = post.call_args[0][0], post.call_args[0][1]
        self.assertEqual(path, '/online/v1/payment/approve')
        self.assertEqual(body['tid'], 'T555')
        self.assertEqual(body['pg_token'], 'PG1')
        self.assertEqual(ev.kind, base.EVENT_PAYMENT_SUCCEEDED)
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.provider_subscription_id, 'S-ABC')
        self.assertEqual(self.sub.provider, 'kakaopay')

    def test_approve_sets_one_month_of_access(self):
        with mock.patch.object(KakaoPayProvider, '_post') as post:
            post.return_value = fake_response(self._approved())
            ev = self.p.approve_return(self.sub, {'pg_token': 'PG1'})
        self.assertIsNotNone(ev.period_end)
        days = (ev.period_end - timezone.now()).days
        self.assertGreaterEqual(days, 27)
        self.assertLessEqual(days, 31)

    def test_approve_without_pg_token_is_refused(self):
        with mock.patch.object(KakaoPayProvider, '_post') as post:
            with self.assertRaises(base.PaymentError):
                self.p.approve_return(self.sub, {})
            post.assert_not_called()

    def test_approve_without_a_pending_tid_is_refused(self):
        """tid 가 없는데 승인 요청이 왔다면 우리가 시작한 결제가 아니다."""
        self.sub.pending_tid = ''
        self.sub.save()
        with mock.patch.object(KakaoPayProvider, '_post') as post:
            with self.assertRaises(base.PaymentError):
                self.p.approve_return(self.sub, {'pg_token': 'PG1'})
            post.assert_not_called()

    def test_pending_tid_is_cleared_after_approval(self):
        """한 번 쓴 tid 로 두 번 승인되면 안 된다."""
        with mock.patch.object(KakaoPayProvider, '_post') as post:
            post.return_value = fake_response(self._approved())
            self.p.approve_return(self.sub, {'pg_token': 'PG1'})
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.pending_tid, '')

    def test_missing_sid_is_an_error(self):
        """정기결제 CID 로 승인했는데 SID 가 없으면 다음 달에 청구할 방법이 없다."""
        with mock.patch.object(KakaoPayProvider, '_post') as post:
            post.return_value = fake_response(self._approved(sid=None))
            with self.assertRaises(base.PaymentError):
                self.p.approve_return(self.sub, {'pg_token': 'PG1'})


@override_settings(KAKAOPAY_SECRET_KEY=SECRET, KAKAOPAY_CID='TCSUBSCRIP')
class KakaoPayRecurringTests(TestCase):
    """2회차 이후. 카카오페이는 알아서 청구해 주지 않는다 — 우리가 건다."""

    def setUp(self):
        self.restaurant = Restaurant.objects.create(name='달빛 이자카야', slug='moonlight')
        self.sub = self.restaurant.subscription
        self.sub.status = 'active'
        self.sub.plan = 'pro'
        self.sub.provider = 'kakaopay'
        self.sub.provider_subscription_id = 'S-ABC'
        self.sub.current_period_end = timezone.now() - timedelta(hours=1)
        self.sub.save()
        self.p = KakaoPayProvider()

    def test_charge_uses_the_stored_sid(self):
        with mock.patch.object(KakaoPayProvider, '_post') as post:
            post.return_value = fake_response({
                'aid': 'A2', 'tid': 'T2', 'sid': 'S-ABC',
                'amount': {'total': 19900}, 'approved_at': '2026-09-19T10:00:00'})
            ev = self.p.charge(self.sub)
        path, body = post.call_args[0][0], post.call_args[0][1]
        self.assertEqual(path, '/online/v1/payment/subscription')
        self.assertEqual(body['sid'], 'S-ABC')
        self.assertEqual(body['cid'], 'TCSUBSCRIP')
        self.assertEqual(body['total_amount'], Subscription.PLAN_PRICES['pro'])
        self.assertEqual(ev.kind, base.EVENT_PAYMENT_SUCCEEDED)

    def test_charge_without_sid_is_refused(self):
        self.sub.provider_subscription_id = ''
        self.sub.save()
        with mock.patch.object(KakaoPayProvider, '_post') as post:
            with self.assertRaises(base.PaymentError):
                self.p.charge(self.sub)
            post.assert_not_called()

    def test_failed_charge_reports_payment_failed(self):
        with mock.patch.object(KakaoPayProvider, '_post') as post:
            post.side_effect = base.PaymentError('카드 한도 초과')
            ev = self.p.charge(self.sub, raise_on_fail=False)
        self.assertEqual(ev.kind, base.EVENT_PAYMENT_FAILED)

    def test_cancel_deactivates_the_sid(self):
        with mock.patch.object(KakaoPayProvider, '_post') as post:
            post.return_value = fake_response({'sid': 'S-ABC', 'status': 'INACTIVE'})
            self.p.cancel(self.sub)
        path, body = post.call_args[0][0], post.call_args[0][1]
        self.assertEqual(path, '/online/v1/payment/manage/subscription/inactive')
        self.assertEqual(body['sid'], 'S-ABC')

    def test_cancel_twice_does_not_explode(self):
        """사장님은 해지 버튼을 두 번 누른다. 이미 해지된 SID 에도 조용해야 한다."""
        self.sub.provider_subscription_id = ''
        self.sub.save()
        with mock.patch.object(KakaoPayProvider, '_post') as post:
            self.p.cancel(self.sub)
            post.assert_not_called()


@override_settings(KAKAOPAY_SECRET_KEY='', KAKAOPAY_CID='')
class KakaoPayUnconfiguredTests(TestCase):
    """키가 없으면 성공한 척하지 않는다."""

    def setUp(self):
        self.restaurant = Restaurant.objects.create(name='달빛 이자카야', slug='moonlight')
        self.p = KakaoPayProvider()

    def test_checkout_without_key_raises_not_configured(self):
        with self.assertRaises(base.PaymentNotConfigured):
            self.p.start_checkout(self.restaurant.subscription, 'pro', 'https://x/')
