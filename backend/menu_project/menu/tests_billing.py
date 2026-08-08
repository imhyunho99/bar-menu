"""
구독·결제 경로 검증.

결제 대행사가 없는 상태에서 확인해야 할 것은 두 가지다.
하나는 '아무도 청구되지 않는다'는 사실이 화면과 상태에 정직하게 남는가,
다른 하나는 대행사가 붙었을 때 웹훅이 남의 구독을 건드릴 수 없는가.
두 번째는 가짜 provider 를 registry 에 한 줄 등록해서 확인한다.
"""

import hashlib
import hmac
import json
from datetime import timedelta
from unittest import mock

from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase, override_settings
from django.utils import timezone

from .billing import base, registry
from .billing.base import BillingEvent, PaymentNotConfigured
from .billing.null import NullPaymentProvider
from .models import Restaurant, Subscription, UserProfile

STUB_SECRET = b'stub-secret'


class StubProvider(base.PaymentProvider):
    """테스트용 대행사. 실제 회사의 API 를 흉내 내지 않고 서명 규약만 흉내 낸다."""

    name = 'stub'

    def start_checkout(self, subscription, plan, return_url):
        return f'https://stub.test/checkout?plan={plan}'

    def cancel(self, subscription):
        return None

    def verify_webhook(self, headers, raw_body):
        expected = hmac.new(STUB_SECRET, raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(headers.get('X-Stub-Signature', ''), expected)

    def parse_webhook(self, raw_body):
        payload = json.loads(raw_body)
        kind = payload.get('type')
        if kind not in base.EVENT_KINDS:
            return None
        period_end = payload.get('period_end')
        return BillingEvent(
            kind=kind,
            provider_subscription_id=payload.get('sub_id', ''),
            period_end=timezone.datetime.fromisoformat(period_end) if period_end else None,
            event_id=payload.get('id', ''),
        )


def stub_registered():
    return mock.patch.dict(registry.PROVIDERS, {StubProvider.name: StubProvider})


class SubscriptionStateTest(TestCase):
    """상태 기계 자체. 화면·URL 과 무관하게 '언제까지 열어 두는가'만 본다."""

    def setUp(self):
        self.restaurant = Restaurant.objects.create(name="알파바", slug="alpha")
        self.subscription = Subscription.objects.create(restaurant=self.restaurant)

    def test_start_trial_sets_14_days(self):
        self.subscription.start_trial()
        self.assertEqual(self.subscription.status, 'trialing')
        remaining = self.subscription.trial_ends_at - timezone.now()
        self.assertGreater(remaining, timedelta(days=13, hours=23))
        self.assertLessEqual(remaining, timedelta(days=14))

    def test_days_left_truncates_toward_zero(self):
        # 남은 시간을 내림한다. 방금 시작한 14일 체험이 '13일 남음' 으로 보인다.
        self.subscription.trial_ends_at = timezone.now() + timedelta(days=3, hours=20)
        self.assertEqual(self.subscription.days_left, 3)

    def test_days_left_never_negative(self):
        self.subscription.trial_ends_at = timezone.now() - timedelta(days=5)
        self.assertEqual(self.subscription.days_left, 0)

    def test_days_left_is_none_without_any_end_date(self):
        self.assertIsNone(self.subscription.days_left)

    def test_access_until_prefers_paid_period_over_trial(self):
        self.subscription.trial_ends_at = timezone.now() + timedelta(days=2)
        self.subscription.current_period_end = timezone.now() + timedelta(days=30)
        self.assertEqual(self.subscription.access_until, self.subscription.current_period_end)

    def test_usable_while_trialing(self):
        self.subscription.start_trial()
        self.assertTrue(self.subscription.is_usable())

    def test_not_usable_when_trial_expired(self):
        self.subscription.status = 'trialing'
        self.subscription.trial_ends_at = timezone.now() - timedelta(minutes=1)
        self.assertFalse(self.subscription.is_usable())

    def test_usable_while_active_within_period(self):
        self.subscription.status = 'active'
        self.subscription.current_period_end = timezone.now() + timedelta(days=10)
        self.assertTrue(self.subscription.is_usable())

    def test_not_usable_when_active_period_lapsed(self):
        self.subscription.status = 'active'
        self.subscription.current_period_end = timezone.now() - timedelta(days=1)
        self.assertFalse(self.subscription.is_usable())

    def test_past_due_stays_open_even_after_period_end(self):
        # 카드 한 번 실패했다고 영업 중인 가게 메뉴판을 끄지 않는다.
        self.subscription.status = 'past_due'
        self.subscription.current_period_end = timezone.now() - timedelta(days=3)
        self.assertTrue(self.subscription.is_usable())

    def test_canceled_closes_immediately_even_with_time_left(self):
        # 알려진 불일치. 남은 기간이 있어도 해지 즉시 닫힌다.
        # 고치려면 models.py 를 손봐야 해서 지금은 현 동작을 기록만 해둔다.
        self.subscription.status = 'canceled'
        self.subscription.current_period_end = timezone.now() + timedelta(days=20)
        self.assertFalse(self.subscription.is_usable())


class BillingPermissionTest(TestCase):
    """남의 매장 구독 화면에 손댈 수 없어야 한다."""

    def setUp(self):
        self.alpha = Restaurant.objects.create(name="알파바", slug="alpha")
        self.beta = Restaurant.objects.create(name="베타바", slug="beta")

        self.owner = User.objects.create_user(username='alpha_owner', password='pw', is_staff=True)
        UserProfile.objects.create(user=self.owner, restaurant=self.alpha)

        self.superuser = User.objects.create_superuser(username='root', password='pw')

    def _urls(self, slug):
        return {
            'home': f'/{slug}/admin/billing/',
            'start': f'/{slug}/admin/billing/start/',
            'cancel': f'/{slug}/admin/billing/cancel/',
        }

    def test_anonymous_is_redirected_to_login(self):
        response = self.client.get(self._urls('alpha')['home'])
        self.assertEqual(response.status_code, 302)
        self.assertNotIn('알파바', response.get('Location', ''))

    def test_owner_sees_own_billing_home(self):
        self.client.force_login(self.owner)
        response = self.client.get(self._urls('alpha')['home'])
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/billing.html')

    def test_owner_is_forbidden_on_another_tenant(self):
        self.client.force_login(self.owner)
        urls = self._urls('beta')
        self.assertEqual(self.client.get(urls['home']).status_code, 403)
        self.assertEqual(self.client.post(urls['start'], {'plan': 'pro'}).status_code, 403)
        self.assertEqual(self.client.post(urls['cancel']).status_code, 403)

    def test_forbidden_request_does_not_create_a_subscription(self):
        self.client.force_login(self.owner)
        self.client.post(self._urls('beta')['cancel'])
        self.assertFalse(Subscription.objects.filter(restaurant=self.beta).exists())

    def test_superuser_may_view_any_tenant(self):
        self.client.force_login(self.superuser)
        self.assertEqual(self.client.get(self._urls('beta')['home']).status_code, 200)

    def test_post_only_views_reject_get(self):
        self.client.force_login(self.owner)
        urls = self._urls('alpha')
        self.assertEqual(self.client.get(urls['start']).status_code, 405)
        self.assertEqual(self.client.get(urls['cancel']).status_code, 405)

    def test_billing_home_starts_a_trial_for_a_restaurant_without_one(self):
        self.client.force_login(self.owner)
        self.client.get(self._urls('alpha')['home'])
        subscription = Subscription.objects.get(restaurant=self.alpha)
        self.assertEqual(subscription.status, 'trialing')
        self.assertIsNotNone(subscription.trial_ends_at)


class NullProviderTest(TestCase):
    """연동 전 기본 provider 가 결제한 척하지 않는지."""

    def setUp(self):
        self.restaurant = Restaurant.objects.create(name="알파바", slug="alpha")
        self.owner = User.objects.create_user(username='alpha_owner', password='pw', is_staff=True)
        UserProfile.objects.create(user=self.owner, restaurant=self.restaurant)
        self.client.force_login(self.owner)

    def test_default_provider_is_null(self):
        self.assertEqual(registry.get_provider().name, 'null')

    def test_null_checkout_raises_instead_of_returning_a_url(self):
        with self.assertRaises(PaymentNotConfigured):
            NullPaymentProvider().start_checkout(None, 'pro', 'https://example.test/back')

    def test_null_provider_rejects_every_webhook(self):
        self.assertFalse(NullPaymentProvider().verify_webhook({}, b'{}'))

    def test_start_checkout_says_so_instead_of_faking_success(self):
        response = self.client.post('/alpha/admin/billing/start/', {'plan': 'pro'}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '아직 결제 연동 전입니다')

        subscription = Subscription.objects.get(restaurant=self.restaurant)
        self.assertEqual(subscription.status, 'trialing')
        self.assertEqual(subscription.plan, 'entry')          # 요금제가 바뀌지 않았다
        self.assertEqual(subscription.provider, '')           # 대행사에 아무것도 안 만들었다
        self.assertEqual(subscription.provider_subscription_id, '')
        self.assertIsNone(subscription.current_period_end)    # 결제 주기도 생기지 않았다

    def test_unknown_plan_is_rejected(self):
        response = self.client.post('/alpha/admin/billing/start/', {'plan': 'diamond'}, follow=True)
        self.assertContains(response, '알 수 없는 요금제입니다')

    def test_billing_home_shows_the_countdown_the_model_reports(self):
        subscription = Subscription.objects.create(restaurant=self.restaurant)
        subscription.trial_ends_at = timezone.now() + timedelta(days=9, hours=5)
        subscription.save()

        response = self.client.get('/alpha/admin/billing/')
        self.assertContains(response, '9일 남음')
        self.assertContains(response, '무료 체험')

    def test_billing_home_warns_that_payment_is_not_wired(self):
        response = self.client.get('/alpha/admin/billing/')
        self.assertContains(response, '아직 결제 연동 전입니다')

    def test_cancel_works_without_a_provider_and_keeps_the_paid_window(self):
        subscription = Subscription.objects.create(restaurant=self.restaurant)
        subscription.status = 'active'
        subscription.current_period_end = timezone.now() + timedelta(days=20)
        subscription.save()

        self.client.post('/alpha/admin/billing/cancel/')

        subscription.refresh_from_db()
        self.assertEqual(subscription.status, 'canceled')
        self.assertIsNotNone(subscription.canceled_at)
        # 남은 이용 기간은 지우지 않는다 — 이미 낸 돈이다.
        self.assertIsNotNone(subscription.current_period_end)
        self.assertGreater(subscription.access_until, timezone.now())

    def test_cancel_twice_keeps_the_first_cancel_time(self):
        Subscription.objects.create(restaurant=self.restaurant).start_trial().save()
        self.client.post('/alpha/admin/billing/cancel/')
        first = Subscription.objects.get(restaurant=self.restaurant).canceled_at
        self.client.post('/alpha/admin/billing/cancel/')
        self.assertEqual(Subscription.objects.get(restaurant=self.restaurant).canceled_at, first)


class RegistryTest(TestCase):
    def test_registering_a_provider_is_one_line(self):
        with stub_registered(), override_settings(PAYMENT_PROVIDER='stub'):
            self.assertIsInstance(registry.get_provider(), StubProvider)

    def test_unknown_setting_fails_loudly(self):
        # 오타가 조용히 '결제 없음' 으로 되돌아가면 아무도 눈치채지 못한다.
        with override_settings(PAYMENT_PROVIDER='typo'):
            with self.assertRaises(ImproperlyConfigured):
                registry.get_provider()

    def test_unknown_name_lookup_returns_none(self):
        self.assertIsNone(registry.get_provider_by_name('nobody'))


class WebhookTest(TestCase):
    def setUp(self):
        self.restaurant = Restaurant.objects.create(name="알파바", slug="alpha")
        self.other = Restaurant.objects.create(name="베타바", slug="beta")

        self.subscription = Subscription.objects.create(
            restaurant=self.restaurant,
            status='trialing',
            provider='stub',
            provider_subscription_id='sub_alpha',
        )
        self.subscription.start_trial()
        self.subscription.save()

    def _post(self, body: bytes, signature=None, provider='stub'):
        if signature is None:
            signature = hmac.new(STUB_SECRET, body, hashlib.sha256).hexdigest()
        return self.client.post(
            f'/billing/webhook/{provider}/',
            data=body,
            content_type='application/json',
            headers={'x-stub-signature': signature},
        )

    def _payload(self, kind, period_end=None, sub_id='sub_alpha', event_id='evt_1'):
        body = {'type': kind, 'sub_id': sub_id, 'id': event_id}
        if period_end:
            body['period_end'] = period_end.isoformat()
        return json.dumps(body).encode()

    def test_unknown_provider_is_404(self):
        response = self.client.post('/billing/webhook/nobody/', data=b'{}',
                                    content_type='application/json')
        self.assertEqual(response.status_code, 404)

    def test_get_is_not_allowed(self):
        with stub_registered():
            self.assertEqual(self.client.get('/billing/webhook/stub/').status_code, 405)

    def test_bad_signature_is_400_and_changes_nothing(self):
        payload = self._payload(base.EVENT_SUBSCRIPTION_CANCELED)
        with stub_registered():
            response = self._post(payload, signature='deadbeef')
        self.assertEqual(response.status_code, 400)
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.status, 'trialing')

    def test_tampered_body_invalidates_the_signature(self):
        payload = self._payload(base.EVENT_SUBSCRIPTION_CANCELED)
        signature = hmac.new(STUB_SECRET, payload, hashlib.sha256).hexdigest()
        tampered = self._payload(base.EVENT_SUBSCRIPTION_CANCELED, sub_id='sub_beta')
        with stub_registered():
            response = self._post(tampered, signature=signature)
        self.assertEqual(response.status_code, 400)

    def test_null_provider_webhook_is_rejected(self):
        # 대행사가 없는데 도착한 웹훅은 정상 트래픽이 아니다.
        self.assertEqual(self._post(b'{}', signature='whatever', provider='null').status_code, 400)

    def test_payment_succeeded_activates_and_extends(self):
        period_end = (timezone.now() + timedelta(days=30)).replace(microsecond=0)
        with stub_registered():
            response = self._post(self._payload(base.EVENT_PAYMENT_SUCCEEDED, period_end))
        self.assertEqual(response.status_code, 200)

        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.status, 'active')
        self.assertEqual(self.subscription.current_period_end, period_end)
        self.assertTrue(self.subscription.is_usable())

    def test_redelivery_does_not_double_apply(self):
        period_end = (timezone.now() + timedelta(days=30)).replace(microsecond=0)
        payload = self._payload(base.EVENT_PAYMENT_SUCCEEDED, period_end)
        with stub_registered():
            self._post(payload)
            self._post(payload)  # 대행사 재전송

        self.subscription.refresh_from_db()
        # 두 번 적용됐다면 결제 주기가 60일 뒤로 밀렸을 것이다.
        self.assertEqual(self.subscription.current_period_end, period_end)

    def test_stale_event_cannot_rewind_the_period(self):
        current = (timezone.now() + timedelta(days=30)).replace(microsecond=0)
        stale = (timezone.now() - timedelta(days=1)).replace(microsecond=0)
        with stub_registered():
            self._post(self._payload(base.EVENT_PAYMENT_SUCCEEDED, current))
            self._post(self._payload(base.EVENT_PAYMENT_SUCCEEDED, stale, event_id='evt_old'))

        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.current_period_end, current)

    def test_cancel_event_is_idempotent(self):
        payload = self._payload(base.EVENT_SUBSCRIPTION_CANCELED)
        with stub_registered():
            self._post(payload)
            self.subscription.refresh_from_db()
            first_canceled_at = self.subscription.canceled_at
            self._post(payload)  # 같은 사건 재전송

        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.status, 'canceled')
        self.assertEqual(self.subscription.canceled_at, first_canceled_at)

    def test_payment_failed_marks_past_due_without_closing_the_menu(self):
        with stub_registered():
            self._post(self._payload(base.EVENT_PAYMENT_FAILED))

        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.status, 'past_due')
        self.assertTrue(self.subscription.is_usable())

    def test_payment_failed_does_not_revive_a_canceled_subscription(self):
        self.subscription.status = 'canceled'
        self.subscription.save()
        with stub_registered():
            self._post(self._payload(base.EVENT_PAYMENT_FAILED))

        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.status, 'canceled')

    def test_event_for_an_unknown_subscription_is_swallowed(self):
        with stub_registered():
            response = self._post(self._payload(base.EVENT_SUBSCRIPTION_CANCELED, sub_id='sub_nobody'))
        # 재시도해도 영원히 주인을 못 찾으므로 200 으로 끊는다.
        self.assertEqual(response.status_code, 200)
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.status, 'trialing')

    def test_webhook_cannot_reach_another_providers_subscription(self):
        # 같은 구독 ID 라도 provider 가 다르면 남의 것이다.
        Subscription.objects.create(
            restaurant=self.other, provider='other', provider_subscription_id='sub_alpha'
        )
        with stub_registered():
            self._post(self._payload(base.EVENT_SUBSCRIPTION_CANCELED))

        self.assertEqual(Subscription.objects.get(restaurant=self.other).status, 'trialing')
        self.assertEqual(Subscription.objects.get(restaurant=self.restaurant).status, 'canceled')

    def test_uninteresting_event_is_ignored(self):
        with stub_registered():
            response = self._post(json.dumps({'type': 'invoice.drafted'}).encode())
        self.assertEqual(response.status_code, 200)
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.status, 'trialing')
