"""
7일 무료 체험.

체험은 한 번 폐지됐다가(0047·0048) 되살아났다. 되살리면서 trial_ends_at 필드는
만들지 않고 current_period_end 를 재사용한다 — is_usable 이 이미 '상태 먼저,
날짜 나중' 으로 보기 때문에 trialing 은 날짜 분기로 자연히 떨어진다. 그 성질에
기대는 코드라, 여기서 못박아 두지 않으면 다음 사람이 is_usable 을 손보다가
조용히 깨뜨린다.
"""

import os
import re
from datetime import timedelta
from io import StringIO
from pathlib import Path
from unittest import mock

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from . import notifications
from .models import Restaurant, Subscription, UserProfile


class TrialStartsAtSignupTests(TestCase):
    """가입한 매장은 7일 동안 열려 있어야 한다."""

    def test_signup_starts_a_seven_day_trial(self):
        response = self.client.post('/signup/', {
            'email': 'owner@example.com',
            'password': 'ssamdi-9910-pass',
            'name': '달빛 이자카야',
            'slug': 'moonlight',
        })
        self.assertEqual(response.status_code, 302)

        subscription = Restaurant.objects.get(slug='moonlight').subscription
        self.assertEqual(subscription.status, 'trialing')
        self.assertIsNotNone(subscription.current_period_end)
        remaining = subscription.current_period_end - timezone.now()
        # 7일에서 테스트가 도는 몇 초를 뺀 값. 정확히 7일을 요구하면 느린 CI 에서 깨진다.
        self.assertGreater(remaining, timedelta(days=6, hours=23))
        self.assertLessEqual(remaining, timedelta(days=7))

    def test_trial_days_is_seven(self):
        """숫자가 코드 여기저기 흩어지면 화면과 실제 만료일이 어긋난다."""
        self.assertEqual(Subscription.TRIAL_DAYS, 7)

    def test_trialing_is_a_known_status(self):
        """choices 에 없으면 admin 드롭다운에서 고를 수 없고 화면에 코드가 그대로 뜬다."""
        subscription = Subscription(status='trialing')
        self.assertEqual(subscription.get_status_display(), '무료 체험')


class ExpireTrialsCommandTests(TestCase):
    """
    체험 만료 스윕.

    손님 화면이 닫히는 건 is_usable 의 실시간 날짜 비교라 이 명령과 무관하게
    정시에 일어난다. 이 명령이 하는 일은 두 가지다: 상태를 unpaid 로 내려
    화면과 목록에서 '끝났다' 고 읽히게 하는 것, 그리고 우리에게 알리는 것.

    charge_subscriptions 에 얹지 않은 이유가 있다. 그쪽은 첫 줄이
    get_provider() 이고 PaymentNotConfigured 를 만나면 통째로 return 한다.
    결제 대행사가 붙기 전인 지금 거기 섞으면 만료 스윕이 아예 돌지 않는다.
    """

    def _restaurant(self, slug, status, ends_in):
        restaurant = Restaurant.objects.create(name=slug, slug=slug)
        sub = restaurant.subscription
        sub.status = status
        sub.current_period_end = None if ends_in is None else timezone.now() + ends_in
        sub.save()
        return restaurant

    def _run(self, **opts):
        out = StringIO()
        call_command('expire_trials', stdout=out, **opts)
        return out.getvalue()

    def test_lapsed_trial_becomes_unpaid(self):
        restaurant = self._restaurant('lapsed', 'trialing', -timedelta(minutes=1))
        self._run()
        restaurant.subscription.refresh_from_db()
        self.assertEqual(restaurant.subscription.status, 'unpaid')

    def test_running_trial_is_left_alone(self):
        restaurant = self._restaurant('running', 'trialing', timedelta(days=2))
        self._run()
        restaurant.subscription.refresh_from_db()
        self.assertEqual(restaurant.subscription.status, 'trialing')

    def test_partner_is_never_touched(self):
        """
        파트너는 옛 날짜를 달고 있을 수 있다. 상태가 아니라 날짜로 대상을
        고르면 영업 중인 가게가 한꺼번에 미결제로 떨어진다.
        """
        restaurant = self._restaurant('partner', 'partner', -timedelta(days=365))
        self._run()
        restaurant.subscription.refresh_from_db()
        self.assertEqual(restaurant.subscription.status, 'partner')

    def test_lapsed_paid_subscription_is_not_touched(self):
        """결제한 매장의 만료는 charge_subscriptions 의 몫이다. 여기서 내리면 청구가 사라진다."""
        restaurant = self._restaurant('paid', 'active', -timedelta(days=1))
        self._run()
        restaurant.subscription.refresh_from_db()
        self.assertEqual(restaurant.subscription.status, 'active')

    def test_dry_run_changes_nothing(self):
        restaurant = self._restaurant('lapsed', 'trialing', -timedelta(minutes=1))
        output = self._run(dry_run=True)
        restaurant.subscription.refresh_from_db()
        self.assertEqual(restaurant.subscription.status, 'trialing')
        self.assertIn('lapsed', output)

    def test_it_notifies_us_once_per_expiry(self):
        """
        두 번 알리면 우리가 알림을 믿지 않게 되고, 안 알리면 사장님을 놓친다.
        상태를 내리는 것과 알리는 것이 같은 판정을 써야 한다.
        """
        self._restaurant('lapsed', 'trialing', -timedelta(minutes=1))
        with mock.patch('menu.notifications.send_trial_expired_notification') as notify:
            self._run()
            self._run()
        self.assertEqual(notify.call_count, 1)


class TrialNotificationTests(TestCase):
    """
    가입과 만료를 우리가 알아야 한다.

    결제가 아직 없으므로 청구는 사람이 한다. 그 사람이 움직이려면 두 순간을
    알아야 한다: 누가 들어왔는가, 누구의 체험이 끝났는가. 연락처가 페이로드에
    없으면 알림을 받고도 할 수 있는 일이 없다.
    """

    def setUp(self):
        self.restaurant = Restaurant.objects.create(name='달빛 이자카야', slug='moonlight')
        self.owner = User.objects.create_user('owner@example.com', email='owner@example.com',
                                              password='jazz-bar-9137')
        UserProfile.objects.create(user=self.owner, restaurant=self.restaurant, phone='050-1234-5678')

    def _fields(self, payload):
        return {f['name']: f['value'] for f in payload['embeds'][0]['fields']}

    def test_signup_payload_carries_a_way_to_reach_the_owner(self):
        fields = self._fields(notifications.build_signup_payload(self.restaurant))
        self.assertIn('달빛 이자카야', str(fields))
        self.assertIn('moonlight', str(fields))
        self.assertIn('owner@example.com', str(fields))
        self.assertIn('050-1234-5678', str(fields))

    def test_signup_payload_says_when_the_trial_ends(self):
        """언제까지 두고 볼지 모르면 알림을 받아도 일정을 잡을 수 없다."""
        payload = notifications.build_signup_payload(self.restaurant)
        ends = self.restaurant.subscription.current_period_end
        self.assertIn(f'{ends:%Y-%m-%d}', str(payload))

    def test_signup_payload_survives_a_missing_phone(self):
        """전화번호는 선택 입력이다. 없다고 가입 알림이 터지면 가입이 막힌다."""
        UserProfile.objects.filter(user=self.owner).update(phone='')
        payload = notifications.build_signup_payload(self.restaurant)
        self.assertIn('owner@example.com', str(payload))

    def test_signup_payload_survives_a_restaurant_with_no_manager(self):
        """어드민에서 매장만 먼저 만드는 경로가 있다. 거기서 터지면 매장 생성이 막힌다."""
        orphan = Restaurant.objects.create(name='주인 없는 가게', slug='orphan')
        self.assertIn('orphan', str(notifications.build_signup_payload(orphan)))

    def test_trial_expired_payload_carries_a_way_to_reach_the_owner(self):
        fields = self._fields(
            notifications.build_trial_expired_payload(self.restaurant.subscription))
        self.assertIn('달빛 이자카야', str(fields))
        self.assertIn('owner@example.com', str(fields))
        self.assertIn('050-1234-5678', str(fields))

    def test_nothing_is_sent_without_a_webhook(self):
        """스테이징엔 웹훅이 없다. 거기서 예외가 나면 가입 자체가 실패한다."""
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(notifications.send_signup_notification(self.restaurant))
            self.assertIsNone(
                notifications.send_trial_expired_notification(self.restaurant.subscription))


class SignupCollectsAContactTests(TestCase):
    """청구를 사람이 하는 동안, 연락 수단은 가입 때 받아두는 수밖에 없다."""

    FORM = {
        'email': 'owner@example.com',
        'password': 'jazz-bar-9137',
        'name': '달빛 이자카야',
        'slug': 'moonlight',
    }

    def test_signup_stores_the_phone_number(self):
        self.client.post('/signup/', dict(self.FORM, phone='050-1234-5678'))
        profile = UserProfile.objects.get(user__username='owner@example.com')
        self.assertEqual(profile.phone, '050-1234-5678')

    def test_phone_is_optional(self):
        """필수로 만들면 가입 폼에서 이탈한다. 이메일만으로도 연락은 된다."""
        response = self.client.post('/signup/', self.FORM)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(UserProfile.objects.get(user__username='owner@example.com').phone, '')

    def test_signup_notifies_us(self):
        with mock.patch('menu.onboarding_views.notifications.send_signup_notification') as notify:
            self.client.post('/signup/', dict(self.FORM, phone='050-1234-5678'))
        notify.assert_called_once()
        self.assertEqual(notify.call_args[0][0].slug, 'moonlight')


class TrialIsNeverChargedTests(TestCase):
    """
    체험 매장에 청구를 걸면 안 된다.

    charge_subscriptions 는 provider_subscription_id 가 빈 것을 걸러내므로
    지금은 SID 가 없어서 지나간다. 하지만 그건 우연이다 — 누군가 그 exclude 를
    손보는 순간 체험 매장에 실제 결제가 나간다. 상태로도 막혀 있음을 못박는다.
    """

    def test_billable_statuses_exclude_trialing(self):
        from menu.management.commands.charge_subscriptions import BILLABLE

        self.assertNotIn('trialing', BILLABLE)

    def test_charge_command_skips_a_trialing_subscription_with_a_sid(self):
        restaurant = Restaurant.objects.create(name='체험 중', slug='trialing-store')
        sub = restaurant.subscription
        sub.current_period_end = timezone.now() - timedelta(days=1)
        sub.provider = 'kakaopay'
        sub.provider_subscription_id = 'S-LEFTOVER'
        sub.save()

        # 명령이 get_provider 를 자기 이름공간으로 import 해 왔다. registry 쪽을
        # 패치하면 이미 바인딩된 이름은 그대로라 mock 이 헛돌고, 청구가 걸려도
        # 테스트가 통과한다.
        with mock.patch(
            'menu.management.commands.charge_subscriptions.get_provider'
        ) as provider:
            call_command('charge_subscriptions', stdout=StringIO())
            provider.return_value.charge.assert_not_called()

        sub.refresh_from_db()
        self.assertEqual(sub.status, 'trialing')


class BillingPageShowsTheTrialTests(TestCase):
    """결제 화면은 사장님이 '내 상태가 뭔가' 를 확인하러 오는 곳이다."""

    def setUp(self):
        self.restaurant = Restaurant.objects.create(name='달빛 이자카야', slug='moonlight')
        owner = User.objects.create_user('owner', password='pw', is_staff=True)
        UserProfile.objects.create(user=owner, restaurant=self.restaurant)
        self.client.force_login(owner)
        self.url = '/moonlight/admin/billing/'

    def test_trialing_store_sees_when_the_trial_ends_and_what_happens_then(self):
        response = self.client.get(self.url)
        self.assertContains(response, '무료 체험')
        self.assertContains(response, '체험이 끝나면')

    def test_trialing_store_is_not_told_its_screen_is_closed(self):
        """체험 중에는 실제로 열려 있다. 닫혔다고 하면 사장님이 개업을 미룬다."""
        response = self.client.get(self.url)
        self.assertNotContains(response, '손님 화면이 닫혀 있습니다')


class MarketingPromisesTheRightTrialTests(TestCase):
    """
    랜딩이 약속하는 체험 기간과 코드가 주는 기간이 같아야 한다.

    가격이 두 곳에 적혀 갈리는 걸 tests_pricing 이 막듯이, 기간도 같은 종류의
    사고다. TRIAL_DAYS 를 고치고 랜딩을 안 고치면 손님은 14일인 줄 알고 가입해
    7일 만에 닫힌 화면을 본다. 거짓말한 쪽이 되는 건 우리다.
    """

    FRONTEND = Path(__file__).resolve().parents[3] / 'frontend' / 'src'

    # 가입 버튼이 있는 곳. 버튼 옆에서 며칠인지 말하지 않으면 손님은
    # '무료' 만 읽고 영원히 무료인 줄 안다.
    SIGNUP_PAGES = [
        'lib/marketing-content.ts',
        'app/(marketing)/page.tsx',
        'app/(marketing)/pricing/page.tsx',
        'app/(marketing)/guide/page.tsx',
    ]

    def _promised_days(self, source):
        return set(re.findall(r'(\d+)일(?:\s*동안)?\s*무료', source))

    def test_every_signup_page_states_the_actual_trial_length(self):
        for relative in self.SIGNUP_PAGES:
            with self.subTest(page=relative):
                source = (self.FRONTEND / relative).read_text(encoding='utf-8')
                promised = self._promised_days(source)
                self.assertTrue(promised, f'{relative} 에 무료 체험 기간이 적혀 있지 않습니다')
                self.assertEqual(
                    promised, {str(Subscription.TRIAL_DAYS)},
                    f'{relative} 이 약속한 기간과 TRIAL_DAYS({Subscription.TRIAL_DAYS})가 다릅니다')
