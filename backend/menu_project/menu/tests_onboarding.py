"""
셀프 가입 · 온보딩 체크리스트.

여기서 지키려는 건 두 가지다. 하나, 가입 한 번에 User·Restaurant·
UserProfile·Subscription 네 덩어리가 빠짐없이 생기는가. 둘, 손님 주소가
될 slug 가 시스템 경로에 가려지지 않는가. 후자는 실패해도 가입은 성공한
것처럼 보이고, 사고는 인쇄된 QR 을 붙인 개업 당일에 드러난다.
"""

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import get_resolver
from django.urls.resolvers import RoutePattern

from .models import Category, MenuItem, Restaurant, SiteSettings, Subscription, UserProfile
from .onboarding_views import RESERVED_SLUGS

SIGNUP_URL = '/signup/'
CHECK_SLUG_URL = '/signup/check-slug/'

GOOD_FORM = {
    'email': 'owner@example.com',
    'password': 'jazz-bar-9137',
    'name': '달빛 이자카야',
    'slug': 'moonlight',
}


class SignupTests(TestCase):
    def test_signup_creates_all_four_objects_and_starts_trial(self):
        response = self.client.post(SIGNUP_URL, GOOD_FORM)

        self.assertRedirects(response, '/moonlight/admin/start/')

        user = User.objects.get(username='owner@example.com')
        self.assertTrue(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.check_password('jazz-bar-9137'))

        restaurant = Restaurant.objects.get(slug='moonlight')
        self.assertEqual(restaurant.name, '달빛 이자카야')

        profile = UserProfile.objects.get(user=user)
        self.assertEqual(profile.restaurant, restaurant)

        subscription = Subscription.objects.get(restaurant=restaurant)
        self.assertEqual(subscription.status, 'trialing')
        self.assertIsNotNone(subscription.trial_ends_at)
        self.assertEqual(subscription.days_left, Subscription.TRIAL_DAYS - 1)
        self.assertTrue(subscription.is_usable())

        # Restaurant post_save 시그널이 만드는 것. 여기서 또 만들면 두 개가 된다.
        self.assertEqual(SiteSettings.objects.filter(restaurant=restaurant).count(), 1)

    def test_signup_logs_the_owner_in(self):
        self.client.post(SIGNUP_URL, GOOD_FORM)
        self.assertEqual(int(self.client.session['_auth_user_id']),
                         User.objects.get(username='owner@example.com').pk)

    def test_duplicate_slug_rejected(self):
        Restaurant.objects.create(name='기존 가게', slug='moonlight')

        response = self.client.post(SIGNUP_URL, GOOD_FORM)

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, '이미 사용 중인 매장 주소', status_code=400)
        self.assertFalse(User.objects.filter(username='owner@example.com').exists())

    def test_duplicate_slug_ignores_case(self):
        Restaurant.objects.create(name='기존 가게', slug='Moonlight')
        response = self.client.post(SIGNUP_URL, GOOD_FORM)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Restaurant.objects.count(), 1)

    def test_reserved_slugs_rejected(self):
        for reserved in ['admin', 'api', 'signup', 'billing', 'static', 'media', 'contact-us', 'login']:
            with self.subTest(slug=reserved):
                response = self.client.post(SIGNUP_URL, dict(GOOD_FORM, slug=reserved))
                self.assertEqual(response.status_code, 400)
                self.assertContains(response, '시스템이 쓰는 주소', status_code=400)
                self.assertFalse(Restaurant.objects.filter(slug=reserved).exists())

    def test_reserved_list_covers_every_top_level_url_segment(self):
        """
        RESERVED_SLUGS 가 실제 urlconf 를 따라가는지 본다.

        누군가 menu_project/urls.py 에 최상위 경로를 하나 더 얹으면 그 이름은
        곧바로 '만들 수는 있지만 절대 안 열리는' 매장 주소가 된다. 목록을
        손으로 관리하는 이상, 어긋나는 순간을 잡아주는 건 이 테스트뿐이다.
        """
        for pattern in get_resolver().url_patterns:
            route = (pattern.pattern._route if isinstance(pattern.pattern, RoutePattern)
                     else str(pattern.pattern).lstrip('^'))
            segment = route.split('/')[0]
            if not segment or any(ch in segment for ch in '<>()[]^$*+?\\|'):
                continue  # 변수 자리이거나 루트 — 매장 주소를 가리지 않는다
            with self.subTest(segment=segment):
                self.assertIn(segment, RESERVED_SLUGS)

    def test_duplicate_email_rejected(self):
        User.objects.create_user('owner@example.com', password='whatever-1234')

        response = self.client.post(SIGNUP_URL, GOOD_FORM)

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, '이미 가입된 이메일', status_code=400)
        self.assertFalse(Restaurant.objects.filter(slug='moonlight').exists())

    def test_duplicate_email_rejected_when_only_email_field_matches(self):
        # 손으로 만든 옛 계정은 username 이 이메일이 아니다
        User.objects.create_user('legacy', email='owner@example.com', password='whatever-1234')
        response = self.client.post(SIGNUP_URL, GOOD_FORM)
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, '이미 가입된 이메일', status_code=400)

    def test_invalid_email_rejected(self):
        response = self.client.post(SIGNUP_URL, dict(GOOD_FORM, email='owner-at-example'))
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, '이메일 형식', status_code=400)

    def test_weak_password_rejected(self):
        response = self.client.post(SIGNUP_URL, dict(GOOD_FORM, password='1234'))

        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.exists())
        self.assertFalse(Restaurant.objects.exists())
        # validate_password 가 붙여준 사유가 그대로 보여야 한다
        self.assertContains(response, '비밀번호', status_code=400)

    def test_missing_store_name_rejected(self):
        response = self.client.post(SIGNUP_URL, dict(GOOD_FORM, name='   '))
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, '매장명을 입력해', status_code=400)
        self.assertFalse(Restaurant.objects.exists())

    def test_slug_charset_matches_url_converter(self):
        # <slug:restaurant_slug> 는 [-a-zA-Z0-9_]+ 만 받는다. 통과시키면 404 다.
        for bad in ['달빛', 'moon light', 'moon.light', 'moon/light', 'moon!', '', '---']:
            with self.subTest(slug=bad):
                response = self.client.post(SIGNUP_URL, dict(GOOD_FORM, slug=bad))
                self.assertEqual(response.status_code, 400)
                self.assertFalse(Restaurant.objects.exists())

    def test_slug_is_stored_lowercase(self):
        self.client.post(SIGNUP_URL, dict(GOOD_FORM, slug='MoonLight'))
        self.assertTrue(Restaurant.objects.filter(slug='moonlight').exists())

    def test_form_rerenders_with_entered_values(self):
        response = self.client.post(SIGNUP_URL, {
            'email': 'owner@example.com',
            'password': '1234',            # 여기서 걸린다
            'name': '달빛 이자카야',
            'slug': 'moonlight',
        })

        self.assertEqual(response.status_code, 400)
        content = response.content.decode()
        self.assertIn('value="owner@example.com"', content)
        self.assertIn('달빛 이자카야', content)
        self.assertIn('value="moonlight"', content)
        # 비밀번호는 절대 되돌려주지 않는다
        self.assertNotIn('1234', content)

    def test_get_renders_empty_form(self):
        response = self.client.get(SIGNUP_URL)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'onboarding/signup.html')


class CheckSlugTests(TestCase):
    def test_available_slug(self):
        data = self.client.get(CHECK_SLUG_URL, {'slug': 'moonlight'}).json()
        self.assertTrue(data['available'])
        self.assertIn('moonlight', data['reason'])

    def test_taken_slug(self):
        Restaurant.objects.create(name='기존 가게', slug='moonlight')
        data = self.client.get(CHECK_SLUG_URL, {'slug': 'moonlight'}).json()
        self.assertFalse(data['available'])
        self.assertIn('이미 사용 중', data['reason'])

    def test_reserved_slug(self):
        for reserved in ['admin', 'api']:
            with self.subTest(slug=reserved):
                data = self.client.get(CHECK_SLUG_URL, {'slug': reserved}).json()
                self.assertFalse(data['available'])
                self.assertIn('시스템이 쓰는 주소', data['reason'])

    def test_bad_charset(self):
        data = self.client.get(CHECK_SLUG_URL, {'slug': 'moon light'}).json()
        self.assertFalse(data['available'])

    def test_empty_slug(self):
        data = self.client.get(CHECK_SLUG_URL).json()
        self.assertFalse(data['available'])
        self.assertTrue(data['reason'])


class OnboardingHomeTests(TestCase):
    def setUp(self):
        self.client.post(SIGNUP_URL, GOOD_FORM)
        self.restaurant = Restaurant.objects.get(slug='moonlight')
        self.user = User.objects.get(username='owner@example.com')
        self.url = '/moonlight/admin/start/'

    def test_anonymous_is_sent_to_store_login(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertRedirects(response, '/moonlight/admin/login/')

    def test_fresh_store_shows_nothing_done(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'onboarding/start.html')
        self.assertEqual(response.context['menu_count'], 0)
        self.assertEqual(response.context['category_count'], 0)
        self.assertEqual(response.context['done_count'], 0)
        self.assertEqual(response.context['days_left'], Subscription.TRIAL_DAYS - 1)

    def test_menu_step_flips_on_real_rows(self):
        category = Category.objects.create(name='사시미', restaurant=self.restaurant)
        MenuItem.objects.create(name='모둠 사시미', price='38,000', description='',
                                category=category, restaurant=self.restaurant)

        response = self.client.get(self.url)

        self.assertEqual(response.context['menu_count'], 1)
        self.assertEqual(response.context['category_count'], 1)
        steps = {step['key']: step for step in response.context['steps']}
        self.assertTrue(steps['menu']['done'])
        self.assertFalse(steps['qr']['locked'])
        self.assertEqual(response.context['done_count'], 1)

    def test_counts_ignore_other_restaurants_rows(self):
        other = Restaurant.objects.create(name='남의 가게', slug='other')
        other_category = Category.objects.create(name='구이', restaurant=other)
        MenuItem.objects.create(name='닭꼬치', price='16,000', description='',
                                category=other_category, restaurant=other)

        response = self.client.get(self.url)

        self.assertEqual(response.context['menu_count'], 0)
        self.assertFalse({s['key']: s for s in response.context['steps']}['menu']['done'])

    def test_billing_step_flips_when_subscription_is_active(self):
        Subscription.objects.filter(restaurant=self.restaurant).update(status='active')
        response = self.client.get(self.url)
        self.assertTrue({s['key']: s for s in response.context['steps']}['billing']['done'])

    def test_step_links_point_at_this_restaurant(self):
        steps = {s['key']: s for s in self.client.get(self.url).context['steps']}
        self.assertEqual(steps['menu']['primary_url'], '/moonlight/admin/menu/import/')
        self.assertEqual(steps['menu']['secondary_url'], '/moonlight/admin/menu/add/')
        self.assertEqual(steps['qr']['primary_url'], '/moonlight/qr/')
        self.assertEqual(steps['billing']['primary_url'], '/moonlight/admin/billing/')
        # 디자인은 아직 Django admin 이 유일한 편집 화면이다
        settings_row = SiteSettings.objects.get(restaurant=self.restaurant)
        self.assertEqual(steps['design']['primary_url'],
                         f'/admin/menu/sitesettings/{settings_row.pk}/change/')

    def test_other_tenant_is_blocked(self):
        Restaurant.objects.create(name='남의 가게', slug='other')
        # 'other' 매장에는 아무 권한이 없는 우리 사장님
        response = self.client.get('/other/admin/start/')
        self.assertEqual(response.status_code, 403)

    def test_superuser_may_look_at_any_store(self):
        self.client.logout()
        User.objects.create_superuser('root', 'root@example.com', 'root-pw-9137')
        self.client.login(username='root', password='root-pw-9137')
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_unknown_restaurant_is_404(self):
        self.assertEqual(self.client.get('/nosuchstore/admin/start/').status_code, 404)
