"""
미리보기 토큰.

사장님이 결제 전에 자기 메뉴판을 실제 화면으로 보는 통로다. 링크 하나로
열리므로, 그 링크가 곧 결제 우회로가 되지 않도록 수명과 대상이 서명에
박혀 있어야 한다.
"""

from django.test import TestCase, override_settings

from django.contrib.auth.models import User

from menu.models import Restaurant, UserProfile
from menu.preview import (
    PREVIEW_MAX_AGE_SECONDS,
    check_preview_token,
    make_preview_token,
)


class PreviewTokenTests(TestCase):
    def test_a_fresh_token_opens_its_own_store(self):
        token = make_preview_token('bid')
        self.assertTrue(check_preview_token('bid', token))

    def test_a_token_does_not_open_another_store(self):
        """서명에 slug 가 들어간다. 한 장 받아서 남의 가게를 열 수 없다."""
        token = make_preview_token('bid')
        self.assertFalse(check_preview_token('sorok', token))

    def test_a_forged_token_is_refused(self):
        self.assertFalse(check_preview_token('bid', 'bid:hand-written'))

    def test_an_empty_token_is_refused(self):
        """?preview= 만 붙여 놓은 주소로 열리면 안 된다."""
        self.assertFalse(check_preview_token('bid', ''))
        self.assertFalse(check_preview_token('bid', None))

    def test_the_lifetime_is_one_day(self):
        self.assertEqual(PREVIEW_MAX_AGE_SECONDS, 60 * 60 * 24)

    def test_an_aged_token_is_refused(self):
        """
        하루면 충분하다. 유출돼도 다음 날 죽으므로 '결제 안 하고 이 링크로
        장사하기' 가 성립하지 않는다.

        시계를 돌리는 대신 max_age 를 음수로 줘서 '이미 지났다' 를 만든다 —
        signing 이 나이를 재는 방식이 그대로 검증된다.
        """
        token = make_preview_token('bid')
        self.assertTrue(check_preview_token('bid', token))
        self.assertFalse(check_preview_token('bid', token, max_age=-1))

    def test_every_token_is_bound_to_the_secret_key(self):
        """키를 갈면 이미 뿌린 링크가 전부 죽는다. 그게 비상구다."""
        token = make_preview_token('bid')
        with self.settings(SECRET_KEY='a-completely-different-key'):
            self.assertFalse(check_preview_token('bid', token))


@override_settings(ENFORCE_SUBSCRIPTION=True)
class PreviewOpensTheGateTests(TestCase):
    """게이트가 켜진 상태에서 토큰 하나가 어디까지 여는가."""

    def setUp(self):
        self.restaurant = Restaurant.objects.create(name='미결제 바', slug='unpaid-bar')
        # 시그널이 unpaid 로 만들어 둔다. 여기서 다시 만들지 않는다.
        self.token = make_preview_token('unpaid-bar')

    def test_unpaid_store_is_closed_without_a_token(self):
        response = self.client.get('/api/v1/restaurants/unpaid-bar/')
        self.assertEqual(response.status_code, 402)

    def test_a_valid_token_opens_the_api(self):
        response = self.client.get(f'/api/v1/restaurants/unpaid-bar/?preview={self.token}')
        self.assertEqual(response.status_code, 200)

    def test_a_valid_token_opens_the_html_page(self):
        response = self.client.get(f'/unpaid-bar/?preview={self.token}')
        self.assertNotEqual(response.status_code, 402)

    def test_another_stores_token_does_not_open_it(self):
        other = make_preview_token('some-other-bar')
        response = self.client.get(f'/api/v1/restaurants/unpaid-bar/?preview={other}')
        self.assertEqual(response.status_code, 402)

    def test_a_forged_token_does_not_open_it(self):
        response = self.client.get('/api/v1/restaurants/unpaid-bar/?preview=nope')
        self.assertEqual(response.status_code, 402)

    def test_preview_does_not_make_the_store_usable(self):
        """
        미리보기는 화면을 열어 줄 뿐 구독 상태가 아니다. 여기가 섞이면
        QR 발행과 입금 확인까지 함께 열린다.
        """
        self.assertFalse(self.restaurant.subscription.is_usable())


@override_settings(CUSTOMER_SITE_URL='https://develop.example.com')
class OwnerGetsAPreviewLinkTests(TestCase):
    """사장님이 그 링크를 어디서 받는가."""

    def setUp(self):
        self.restaurant = Restaurant.objects.create(name='미결제 바', slug='unpaid-bar')
        self.user = User.objects.create_user('owner@example.com', password='pw-12345678')
        UserProfile.objects.create(user=self.user, restaurant=self.restaurant)
        self.client.force_login(self.user)

    def test_dashboard_hands_out_a_working_preview_link(self):
        response = self.client.get('/unpaid-bar/admin/dashboard/')
        self.assertEqual(response.status_code, 200)
        preview_url = response.context['preview_url']
        self.assertIn('preview=', preview_url)

        token = preview_url.split('preview=')[1]
        self.assertTrue(check_preview_token('unpaid-bar', token))

    def test_the_link_is_signed_fresh_not_stored(self):
        """
        누를 때마다 그 자리에서 서명한다. 어제 열어 둔 탭의 링크가 오늘
        죽어 있어도 사장님은 다시 누르면 된다.

        '두 번 부르면 다른 문자열' 로는 확인할 수 없다 — signing 의 타임스탬프가
        초 단위라 같은 초에 부른 둘은 같은 값이다. 방금 서명됐다는 것 자체를
        아주 짧은 max_age 로 본다.
        """
        preview_url = self.client.get('/unpaid-bar/admin/dashboard/').context['preview_url']
        token = preview_url.split('preview=')[1]
        self.assertTrue(check_preview_token('unpaid-bar', token, max_age=5))

    def test_the_link_points_at_the_customer_site_not_django(self):
        """
        손님이 실제로 보는 화면은 Next.js 다. Django 가 그리는 /<slug>/ 를
        주면 사장님은 손님이 볼 것과 다른 화면을 확인하게 된다.

        빈 문자열과 대조하면 무엇이든 통과하므로 주소를 직접 적는다.
        """
        response = self.client.get('/unpaid-bar/admin/dashboard/')
        self.assertTrue(
            response.context['preview_url'].startswith('https://develop.example.com/unpaid-bar'),
            response.context['preview_url'],
        )


@override_settings(ENFORCE_SUBSCRIPTION=True, CUSTOMER_SITE_URL='https://develop.example.com')
class DjangoAdminHomeOffersThePreviewTests(TestCase):
    """
    로그인한 사장님이 실제로 도착하는 곳은 Django /admin/ 이다
    (auth_views 가 admin:index 로 보낸다). 미리보기 링크가 커스텀
    대시보드에만 있으면 아무도 보지 못한다.

    게이트를 켜고 본다. 꺼져 있으면 미결제 매장도 실제로 열려 있어서
    미리보기를 권하는 쪽이 거짓말이 된다 — menu_is_live 가 그걸 가른다.
    """

    def setUp(self):
        self.restaurant = Restaurant.objects.create(name='미결제 바', slug='unpaid-bar')
        self.user = User.objects.create_superuser('me@example.com', password='pw-12345678')
        self.client.force_login(self.user)

    def test_an_unopened_store_is_offered_a_preview_link(self):
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'preview=')
        self.assertContains(response, '미리보기 열기')

    def test_an_unopened_store_is_not_sent_to_the_locked_screen(self):
        """
        '손님 화면 보기' 는 공개 전 매장에서 402 잠금 화면으로 간다.
        사장님이 자기 메뉴판을 보려고 누르는 바로 그 버튼이다.
        """
        response = self.client.get('/admin/')
        self.assertNotContains(response, '손님 화면 보기')

    def test_an_open_store_gets_the_real_link(self):
        subscription = self.restaurant.subscription
        subscription.status = 'partner'
        subscription.save(update_fields=['status'])

        response = self.client.get('/admin/')
        self.assertContains(response, '손님 화면 보기')
        self.assertNotContains(response, 'preview=')


@override_settings(ENFORCE_SUBSCRIPTION=True)
class DjangoAdminHomeCarriesTheBannerTests(TestCase):
    """
    배너는 로그인 도착지에 떠야 한다.

    커스텀 대시보드에만 넣으면 이 기능에서 제일 중요한 문장("아직 공개되지
    않았습니다")을 사장님이 영영 보지 못한다 — 로그인하면 /admin/ 으로 가고
    커스텀 대시보드는 일상 경로가 아니다.
    """

    def setUp(self):
        self.restaurant = Restaurant.objects.create(name='미결제 바', slug='unpaid-bar')
        self.user = User.objects.create_superuser('me@example.com', password='pw-12345678')
        self.client.force_login(self.user)

    def test_an_unopened_store_sees_the_banner(self):
        response = self.client.get('/admin/')
        self.assertContains(response, '아직 손님에게 공개되지 않았습니다')
        self.assertContains(response, '/unpaid-bar/admin/billing/')

    def test_a_lapsed_store_is_told_it_closed(self):
        from datetime import timedelta

        from django.utils import timezone

        subscription = self.restaurant.subscription
        subscription.status = 'active'
        subscription.current_period_end = timezone.now() - timedelta(days=1)
        subscription.save()

        response = self.client.get('/admin/')
        self.assertContains(response, '손님 화면이 닫혔습니다')

    def test_an_open_store_sees_no_banner(self):
        subscription = self.restaurant.subscription
        subscription.status = 'partner'
        subscription.save(update_fields=['status'])

        response = self.client.get('/admin/')
        self.assertNotContains(response, '아직 손님에게 공개되지 않았습니다')
        self.assertNotContains(response, '손님 화면이 닫혔습니다')


@override_settings(ENFORCE_SUBSCRIPTION=True)
class TheApiTellsTheFrontWhetherItIsLiveTests(TestCase):
    """
    워터마크는 '토큰이 있는가' 가 아니라 '실제로 안 열렸는가' 를 봐야 한다.

    토큰만 보면, 결제하고 열린 뒤에도 쿠키에 남은 토큰 때문에 사장님이
    최대 하루 동안 자기 영업 중인 메뉴판에서 '손님에게는 아직 보이지
    않습니다' 를 읽는다. 결제가 안 된 줄 안다.
    """

    def setUp(self):
        self.restaurant = Restaurant.objects.create(name='미결제 바', slug='unpaid-bar')
        self.token = make_preview_token('unpaid-bar')

    def _detail(self):
        return self.client.get(
            f'/api/v1/restaurants/unpaid-bar/?preview={self.token}'
        ).json()

    def test_an_unopened_store_reports_not_live(self):
        self.assertFalse(self._detail()['menu_is_live'])

    def test_an_opened_store_reports_live_even_with_a_token(self):
        subscription = self.restaurant.subscription
        subscription.status = 'partner'
        subscription.save(update_fields=['status'])

        self.assertTrue(self._detail()['menu_is_live'])

    def test_the_front_reads_the_flag_and_not_just_the_token(self):
        """
        프론트가 토큰만 보고 배너를 그리면 이 필드는 있으나 마나다.
        layout 이 실제로 menu_is_live 를 함께 보는지 파일에서 확인한다.
        """
        from pathlib import Path

        layout = (
            Path(__file__).resolve().parents[3]
            / 'frontend' / 'src' / 'app' / '[restaurantSlug]' / 'layout.tsx'
        ).read_text(encoding='utf-8')
        self.assertIn('!restaurant.menu_is_live', layout)


class PreviewUrlNeedsExplicitConfigTests(TestCase):
    """
    CUSTOMER_SITE_URL 이 없으면 미리보기 주소를 만들지 않는다.

    예전에는 MARKETING_SITE_URL 로 떨어졌는데, 그 값은 운영을 가리킨다.
    운영에서는 우연히 맞고 develop 에서만 틀리는 폴백이라 제일 나쁘다 —
    테스트하는 곳에서만 깨지고, 깨진 줄도 모른 채 운영 주소를 연다.
    """

    def setUp(self):
        self.restaurant = Restaurant.objects.create(name='미결제 바', slug='unpaid-bar')

    def test_a_configured_site_gives_a_working_link(self):
        from menu.preview import preview_url_for

        with self.settings(CUSTOMER_SITE_URL='https://develop.example.com'):
            url = preview_url_for(self.restaurant)

        self.assertTrue(url.startswith('https://develop.example.com/unpaid-bar?preview='))
        self.assertTrue(check_preview_token('unpaid-bar', url.split('preview=')[1]))

    def test_an_unset_site_gives_nothing_rather_than_a_wrong_link(self):
        from menu.preview import preview_url_for

        with self.settings(CUSTOMER_SITE_URL=''):
            self.assertEqual(preview_url_for(self.restaurant), '')

    def test_a_trailing_slash_does_not_double_up(self):
        from menu.preview import preview_url_for

        with self.settings(CUSTOMER_SITE_URL='https://develop.example.com/'):
            self.assertIn('.com/unpaid-bar?preview=', preview_url_for(self.restaurant))

    @override_settings(CUSTOMER_SITE_URL='')
    def test_the_admin_says_it_is_missing_instead_of_linking_to_production(self):
        user = User.objects.create_superuser('me@example.com', password='pw-12345678')
        self.client.force_login(user)

        with self.settings(ENFORCE_SUBSCRIPTION=True):
            response = self.client.get('/admin/')

        self.assertNotContains(response, 'preview=')
        self.assertContains(response, 'CUSTOMER_SITE_URL')


@override_settings(ENFORCE_SUBSCRIPTION=True)
class PreviewIsReadOnlyTests(TestCase):
    """
    미리보기는 '내 메뉴판이 어떻게 보이는지' 까지다.

    게이트를 통째로 열어 주면 미리보기가 곧 영업이 된다 — 링크를 매일 새로
    받아 뿌리면 결제 없이 주문까지 받을 수 있다. 워터마크는 그걸 못 막는다.
    """

    def setUp(self):
        self.restaurant = Restaurant.objects.create(name='미결제 바', slug='unpaid-bar')
        self.token = make_preview_token('unpaid-bar')

    def _get(self, path):
        return self.client.get(f'/api/v1/restaurants/unpaid-bar/{path}?preview={self.token}')

    def test_reading_the_menu_is_open(self):
        self.assertEqual(self._get('').status_code, 200)
        self.assertEqual(self._get('category-tree/').status_code, 200)

    def test_placing_an_order_is_not(self):
        response = self.client.post(
            f'/api/v1/restaurants/unpaid-bar/orders/?preview={self.token}',
            data={'table_number': '1', 'items': []},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 402)

    def test_the_qr_is_not(self):
        """
        QR 은 인쇄해서 테이블에 붙이는 물건이다. 미리보기로 받을 수 있으면
        '입금 확인 뒤에 발행' 이 아무 의미가 없다.
        """
        self.assertEqual(self._get('qr/').status_code, 402)

    def test_the_qr_stays_shut_even_for_the_logged_in_owner(self):
        """Django 쪽 QR 화면은 토큰과 무관하게 menu_is_live 로 판단한다."""
        from django.contrib.auth.models import User

        user = User.objects.create_user('owner@example.com', password='pw-12345678')
        UserProfile.objects.create(user=user, restaurant=self.restaurant)
        self.client.force_login(user)

        response = self.client.get(f'/unpaid-bar/qr/?preview={self.token}')
        self.assertTemplateUsed(response, 'menu/qr_locked.html')

    def test_an_open_store_still_takes_orders(self):
        """조인 것은 미리보기뿐이다. 결제한 매장은 그대로 돌아야 한다."""
        subscription = self.restaurant.subscription
        subscription.status = 'partner'
        subscription.save(update_fields=['status'])

        response = self.client.post(
            '/api/v1/restaurants/unpaid-bar/orders/',
            data={'table_number': '1', 'items': []},
            content_type='application/json',
        )
        self.assertNotEqual(response.status_code, 402)
