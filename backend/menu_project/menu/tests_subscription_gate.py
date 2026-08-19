"""
구독 게이트 미들웨어.

가장 중요한 성질은 '켜지 않으면 아무것도 막지 않는다' 이다. 결제 대행사가
붙기 전에 이게 켜지면, 체험이 끝난 사장님은 돈 낼 방법도 없이 손님 화면만
꺼진다. 그래서 기본 꺼짐과, 켜졌을 때도 사장님 경로는 열려 있음을 못박는다.
"""

from datetime import timedelta

from importlib import import_module

from django.apps import apps
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone

from .models import Category, Restaurant, Subscription

# 숫자로 시작하는 모듈이라 from ... import 로는 못 가져온다.
partner_migration = import_module('menu.migrations.0048_existing_restaurants_become_partners')


class SubscriptionGateTests(TestCase):
    def setUp(self):
        self.restaurant = Restaurant.objects.create(name="달빛 이자카야", slug="moonlight")
        self.menu_url = f"/{self.restaurant.slug}/"

    def _subscribe(self, **kwargs):
        """매장 생성 시 자동으로 붙은 구독을 주어진 모양으로 맞춘다."""
        sub = self.restaurant.subscription
        for field, value in kwargs.items():
            setattr(sub, field, value)
        sub.save()
        return sub

    # ── 기본값: 꺼져 있다 ──────────────────────────────────────────
    def test_unpaid_store_stays_open_while_enforcement_is_off(self):
        self._subscribe(status='unpaid')
        self.assertNotEqual(self.client.get(self.menu_url).status_code, 402)

    # ── 켰을 때 ────────────────────────────────────────────────────
    @override_settings(ENFORCE_SUBSCRIPTION=True)
    def test_unpaid_store_is_closed_to_customers(self):
        """가입만 하고 결제하지 않은 매장. 이번 정책의 기본 경로다."""
        self._subscribe(status='unpaid')
        response = self.client.get(self.menu_url)
        self.assertEqual(response.status_code, 402)

    @override_settings(ENFORCE_SUBSCRIPTION=True)
    def test_canceled_store_is_closed_to_customers(self):
        self._subscribe(status='canceled')
        response = self.client.get(self.menu_url)
        self.assertEqual(response.status_code, 402)
        self.assertIn('메뉴판을 열 수 없습니다', response.content.decode())

    @override_settings(ENFORCE_SUBSCRIPTION=True)
    def test_partner_store_is_open(self):
        """셀프가입 이전부터 쓰던 매장. 결제와 무관하게 계속 열린다."""
        self._subscribe(status='partner')
        self.assertNotEqual(self.client.get(self.menu_url).status_code, 402)

    @override_settings(ENFORCE_SUBSCRIPTION=True)
    def test_paid_store_is_open(self):
        self._subscribe(status='active', current_period_end=timezone.now() + timedelta(days=20))
        self.assertNotEqual(self.client.get(self.menu_url).status_code, 402)

    @override_settings(ENFORCE_SUBSCRIPTION=True)
    def test_expired_paid_period_is_closed(self):
        self._subscribe(status='active', current_period_end=timezone.now() - timedelta(minutes=1))
        self.assertEqual(self.client.get(self.menu_url).status_code, 402)

    @override_settings(ENFORCE_SUBSCRIPTION=True)
    def test_payment_failure_does_not_close_a_trading_store(self):
        """카드 한 번 실패했다고 영업 중인 가게의 메뉴판을 끄면 그게 더 큰 사고다."""
        self._subscribe(status='past_due', current_period_end=timezone.now() - timedelta(days=2))
        self.assertNotEqual(self.client.get(self.menu_url).status_code, 402)

    @override_settings(ENFORCE_SUBSCRIPTION=True)
    def test_owner_can_still_reach_admin_to_pay(self):
        """되살리러 들어오는 문까지 잠그면 방법이 없어진다."""
        self._subscribe(status='unpaid')
        User.objects.create_user('owner', password='pw', is_staff=True, is_superuser=True)
        self.client.login(username='owner', password='pw')

        response = self.client.get(f"/{self.restaurant.slug}/admin/dashboard/")
        self.assertEqual(response.status_code, 200)

    @override_settings(ENFORCE_SUBSCRIPTION=True)
    def test_never_opened_store_reads_as_preparing_not_as_broken(self):
        """
        아직 결제 전인 매장은 '준비 중' 으로 읽혀야 한다.

        손님에게 결제 사정을 알릴 수는 없다. 사장님이 손님 앞에서 무안해진다.
        그렇다고 '잠시 후 다시' 라고 하면 열릴 리 없는 화면을 계속 새로고침한다.
        """
        self._subscribe(status='unpaid')
        body = self.client.get(self.menu_url).content.decode()
        self.assertIn('준비 중', body)
        self.assertNotIn('결제', body)

    @override_settings(ENFORCE_SUBSCRIPTION=True)
    def test_owner_can_still_get_the_qr_before_paying(self):
        """
        온보딩 체크리스트의 'QR 받기' 는 결제 단계보다 앞에 있고, 결제 화면도
        'QR 준비까지 하실 수 있습니다' 라고 안내한다. 여기를 막으면 그 안내가
        거짓말이 되고 사장님은 오픈 준비를 끝낼 수 없다.
        """
        self._subscribe(status='unpaid')
        self.assertNotEqual(self.client.get(f"/{self.restaurant.slug}/qr/").status_code, 402)

    @override_settings(ENFORCE_SUBSCRIPTION=True)
    def test_store_without_a_subscription_row_is_closed(self):
        """
        구독 레코드가 없으면 잠근다.

        예전에는 통과시켰다. 셀프가입 이전 매장을 봐주려던 예외인데, 그 매장들이
        이제 partner 레코드를 갖게 되면서 이 예외는 '구독 없이 만들어진 매장은
        전부 무료' 라는 구멍으로만 남는다.
        """
        Subscription.objects.filter(restaurant=self.restaurant).delete()
        self.assertEqual(self.client.get(self.menu_url).status_code, 402)


class SubscriptionModelTests(TestCase):
    def setUp(self):
        self.restaurant = Restaurant.objects.create(name="소록", slug="sorok-test")

    def _sub(self, **kwargs):
        """이 매장의 구독을 주어진 모양으로 맞춘다."""
        sub = self.restaurant.subscription
        for field, value in kwargs.items():
            setattr(sub, field, value)
        sub.save()
        return sub

    def test_new_subscription_starts_unpaid(self):
        """체험이 없어졌으므로 아무것도 하지 않은 구독은 미결제다."""
        self.assertEqual(self.restaurant.subscription.status, 'unpaid')

    def test_unpaid_is_not_usable(self):
        """이번 작업의 핵심. 결제 전에는 손님 화면이 열리지 않는다."""
        self.assertFalse(self._sub(status='unpaid').is_usable())

    def test_unpaid_without_any_date_is_not_usable(self):
        """
        날짜가 둘 다 비어 있어도 열리면 안 된다.

        예전 is_usable 은 access_until 이 None 이면 통과시켰다. 체험을 걷어내면
        갓 가입한 매장이 정확히 그 상태가 되므로, 그 경로가 살아 있으면
        게이트를 켜 놓고도 전원이 공짜로 쓰게 된다. 조용히 새는 종류라 못박는다.
        """
        sub = self._sub(status='unpaid', current_period_end=None)
        self.assertIsNone(sub.access_until)
        self.assertFalse(sub.is_usable())

    def test_partner_is_usable_without_any_date(self):
        """무제한 파트너는 결제일도 만료도 없다."""
        sub = self._sub(status='partner')
        self.assertIsNone(sub.access_until)
        self.assertTrue(sub.is_usable())

    def test_partner_ignores_an_expired_period(self):
        """파트너는 날짜를 보지 않는다. 옛 날짜가 남아 있어도 꺼지지 않는다."""
        sub = self._sub(status='partner', current_period_end=timezone.now() - timedelta(days=365))
        self.assertTrue(sub.is_usable())

    def test_canceled_is_not_usable(self):
        self.assertFalse(self._sub(status='canceled').is_usable())

    def test_paid_period_decides_access(self):
        sub = self._sub(status='active', current_period_end=timezone.now() + timedelta(days=25))
        self.assertTrue(sub.is_usable())
        self.assertEqual(sub.access_until, sub.current_period_end)

    def test_trial_machinery_is_gone(self):
        """체험을 되살릴 길을 남겨두지 않는다."""
        self.assertFalse(hasattr(Subscription, 'start_trial'))
        self.assertFalse(hasattr(Subscription, 'TRIAL_DAYS'))
        self.assertNotIn('trialing', dict(Subscription.STATUS_CHOICES))


class ExistingRestaurantsBecomePartnersTests(TestCase):
    """
    0048 데이터 마이그레이션.

    게이트를 deny-by-default 로 뒤집는 순간, 이 마이그레이션이 빠지면 영업 중인
    가게들이 한꺼번에 꺼진다. 되돌릴 수 없는 종류의 사고라 따로 못박는다.
    """

    def _migrate(self):
        partner_migration.make_existing_restaurants_partners(apps, None)

    def _legacy(self, slug, **kwargs):
        """시그널이 붙여 준 구독을 옛 모양으로 되돌린 매장."""
        restaurant = Restaurant.objects.create(name=slug, slug=slug)
        Subscription.objects.filter(restaurant=restaurant).delete()
        if kwargs:
            Subscription.objects.create(restaurant=restaurant, **kwargs)
        return restaurant

    def _status_of(self, restaurant):
        """마이그레이션은 쿼리셋으로 갱신하므로 캐시를 거치지 않고 다시 읽는다."""
        return Subscription.objects.get(restaurant=restaurant).status

    def test_legacy_trial_row_becomes_partner(self):
        restaurant = self._legacy('bid', status='trialing')
        self._migrate()
        self.assertEqual(self._status_of(restaurant), 'partner')

    def test_restaurant_without_a_subscription_gets_one(self):
        restaurant = self._legacy('sorok')
        self._migrate()
        self.assertEqual(self._status_of(restaurant), 'partner')

    def test_migrated_store_stays_open_once_the_gate_is_on(self):
        """마이그레이션의 존재 이유. 여기가 이 파일에서 가장 중요한 단언이다."""
        self._legacy('bid', status='trialing')
        self._migrate()
        with self.settings(ENFORCE_SUBSCRIPTION=True):
            self.assertNotEqual(self.client.get('/bid/').status_code, 402)

    def test_canceled_row_is_left_alone(self):
        """해지한 매장을 파트너로 덮으면 되살아난다."""
        restaurant = self._legacy('closed-bar', status='canceled')
        self._migrate()
        self.assertEqual(self._status_of(restaurant), 'canceled')

    def test_paid_row_is_left_alone(self):
        restaurant = self._legacy('paid-bar', status='active')
        self._migrate()
        self.assertEqual(self._status_of(restaurant), 'active')

    def test_running_twice_changes_nothing(self):
        """마이그레이션을 두 번 태워도 구독이 두 개가 되지 않는다."""
        restaurant = self._legacy('sorok')
        self._migrate()
        self._migrate()
        self.assertEqual(Subscription.objects.filter(restaurant=restaurant).count(), 1)


@override_settings(ENFORCE_SUBSCRIPTION=True)
class ApiGateTests(TestCase):
    """
    손님이 실제로 보는 화면은 Vercel 의 Next.js 이고, 데이터는 이 API 에서 받는다.
    Django 가 그리는 /<slug>/ 페이지를 아무리 잠가도 이쪽이 열려 있으면
    손님 화면은 그대로 뜬다. 게이트의 실효는 여기서 결정된다.

    API 의 URL 인자는 restaurant_slug 가 아니라 slug 라서, RestaurantMiddleware 가
    request.restaurant 를 채우지 않는다. 그래서 별도로 못박는다.
    """

    def setUp(self):
        self.restaurant = Restaurant.objects.create(name="달빛 이자카야", slug="moonlight")
        Category.objects.create(name="위스키", restaurant=self.restaurant)

    def _unpaid(self):
        Subscription.objects.filter(restaurant=self.restaurant).update(status='unpaid')

    def _partner(self):
        Subscription.objects.filter(restaurant=self.restaurant).update(status='partner')

    def test_unpaid_store_menu_api_is_closed(self):
        self._unpaid()
        for path in (
            '/api/v1/restaurants/moonlight/',
            '/api/v1/restaurants/moonlight/categories/',
            '/api/v1/restaurants/moonlight/category-tree/',
            '/api/v1/restaurants/moonlight/search/?q=위스키',
        ):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 402)

    def test_unpaid_store_cannot_take_orders(self):
        """메뉴가 안 보이는 매장이 주문은 받는 상태가 되면 안 된다."""
        self._unpaid()
        response = self.client.post(
            '/api/v1/restaurants/moonlight/orders/',
            data='{}', content_type='application/json',
        )
        self.assertEqual(response.status_code, 402)

    def test_partner_store_api_is_open(self):
        self._partner()
        self.assertEqual(self.client.get('/api/v1/restaurants/moonlight/categories/').status_code, 200)

    def test_contact_form_is_never_gated(self):
        """제휴 문의는 매장에 딸린 경로가 아니다. 여기까지 막으면 신규 유입이 끊긴다."""
        self._unpaid()
        response = self.client.post(
            '/api/v1/contact/',
            data='{"name":"새 가게","contact_info":"a@b.c"}', content_type='application/json',
        )
        self.assertNotEqual(response.status_code, 402)
