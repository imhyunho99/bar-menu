"""
사장님이 Django admin 의 디자인 기능을 실제로 쓸 수 있는가.

메뉴판 레이아웃 빌더와 디자인 설정은 Django admin 에만 있다. 그런데 셀프가입은
is_staff 만 주고 모델 권한을 하나도 주지 않아서, 사장님이 /admin/ 에 들어가면
빈 화면을 봤다(2026-08-23 dev 실측: 등록된 5개 모델 전부 has_view_permission
False). 격리 로직은 잘 짜여 있는데 거기까지 도달을 못 한 상태였다.

여기서 지키는 건 두 가지다. 하나, 사장님이 자기 매장 것을 고칠 수 있는가.
둘, 남의 것과 위험한 것에는 닿지 못하는가. 권한은 늘리기는 쉽고 줄이기는
어렵다 — 이미 받은 사람에게서 뺏는 일이 되기 때문이다.
"""

from django.contrib.admin import site
from django.contrib.auth.models import Group, User
from django.test import RequestFactory, TestCase

from .models import Category, MenuItem, Restaurant, SiteSettings, UserProfile
from .onboarding_views import OWNER_GROUP_NAME

SIGNUP_URL = '/signup/'
GOOD_FORM = {
    'email': 'owner@example.com',
    'password': 'jazz-bar-9137',
    'name': '달빛 이자카야',
    'slug': 'moonlight',
}


class OwnerCanUseTheDesignToolsTests(TestCase):
    def setUp(self):
        self.client.post(SIGNUP_URL, GOOD_FORM)
        self.owner = User.objects.get(username='owner@example.com')
        self.request = RequestFactory().get('/admin/')
        self.request.user = self.owner

    def _admin(self, model):
        return site._registry[model]

    def test_signup_puts_the_owner_in_the_group(self):
        """
        권한을 계정에 직접 붙이지 않고 그룹으로 준다. 나중에 권한을 조정할 때
        이미 가입한 사장님들을 일일이 찾아다니지 않아도 되기 때문이다.
        """
        self.assertTrue(self.owner.groups.filter(name=OWNER_GROUP_NAME).exists())

    def test_owner_can_edit_the_design_settings(self):
        """레이아웃 빌더가 붙어 있는 화면이다. 이게 막히면 디자인 기능 전체가 막힌다."""
        admin = self._admin(SiteSettings)
        self.assertTrue(admin.has_module_permission(self.request), '메뉴에 안 보인다')
        self.assertTrue(admin.has_view_permission(self.request))
        self.assertTrue(admin.has_change_permission(self.request))

    def test_owner_can_manage_categories_and_menu_items(self):
        for model in (Category, MenuItem):
            admin = self._admin(model)
            with self.subTest(model=model.__name__):
                self.assertTrue(admin.has_module_permission(self.request))
                self.assertTrue(admin.has_view_permission(self.request))
                self.assertTrue(admin.has_add_permission(self.request))
                self.assertTrue(admin.has_change_permission(self.request))
                self.assertTrue(admin.has_delete_permission(self.request))

    def test_the_admin_index_is_not_empty(self):
        """
        빈 화면이 아니라는 것 자체를 못박는다. 개별 권한이 다 맞아도 admin 이
        하나도 안 그리면 사장님에게는 '안 된다' 와 같다.
        """
        app_list = site.get_app_list(self.request)
        models = [m['object_name'] for app in app_list for m in app['models']]
        self.assertIn('SiteSettings', models)
        self.assertIn('MenuItem', models)

    def test_owner_reaches_the_admin_index(self):
        self.client.force_login(self.owner)
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '권한이 없습니다')


class OwnerCannotReachDangerousThingsTests(TestCase):
    """권한은 늘리기는 쉽고 줄이기는 어렵다. 주지 않은 것을 못박아 둔다."""

    def setUp(self):
        self.client.post(SIGNUP_URL, GOOD_FORM)
        self.owner = User.objects.get(username='owner@example.com')
        self.request = RequestFactory().get('/admin/')
        self.request.user = self.owner

    def test_cannot_touch_other_restaurants(self):
        admin = site._registry[Restaurant]
        self.assertFalse(admin.has_module_permission(self.request))

    def test_cannot_read_other_peoples_enquiries(self):
        from .models import ContactSubmission

        admin = site._registry[ContactSubmission]
        self.assertFalse(admin.has_view_permission(self.request))

    def test_cannot_manage_users(self):
        admin = site._registry[User]
        self.assertFalse(admin.has_module_permission(self.request))

    def test_cannot_delete_the_design_settings(self):
        """
        지우면 그 매장 손님 화면이 통째로 깨진다. 고칠 수는 있어도 지울 수는 없다.
        """
        admin = site._registry[SiteSettings]
        self.assertFalse(admin.has_delete_permission(self.request))

    def test_only_sees_own_restaurant_rows(self):
        """권한을 준 뒤에도 격리가 유지되는지. 둘은 다른 장치라 함께 확인한다."""
        other = Restaurant.objects.create(name='남의 가게', slug='other')
        mine = Restaurant.objects.get(slug='moonlight')
        Category.objects.create(name='내 카테고리', restaurant=mine)
        Category.objects.create(name='남의 카테고리', restaurant=other)

        rows = site._registry[Category].get_queryset(self.request)
        self.assertEqual([c.name for c in rows], ['내 카테고리'])


class ExistingOwnersGetTheGroupTests(TestCase):
    """
    이미 가입한 사장님들. 마이그레이션 전에 들어온 계정은 그룹이 없어서
    여전히 빈 화면을 본다 — dev 의 tech 매장이 정확히 그 상태였다.
    """

    def test_migration_backfills_existing_owners(self):
        from importlib import import_module

        legacy = User.objects.create_user('legacy@example.com', password='pw', is_staff=True)
        restaurant = Restaurant.objects.create(name='옛 가게', slug='legacy')
        UserProfile.objects.create(user=legacy, restaurant=restaurant)
        legacy.groups.clear()

        migration = import_module('menu.migrations.0053_owner_admin_group')
        migration.grant_owner_group(None, None)

        self.assertTrue(legacy.groups.filter(name=OWNER_GROUP_NAME).exists())

    def test_superusers_are_left_alone(self):
        """슈퍼유저는 그룹이 필요 없고, 넣으면 권한 출처가 둘이 되어 헷갈린다."""
        from importlib import import_module

        boss = User.objects.create_superuser('boss', 'boss@example.com', 'pw')
        import_module('menu.migrations.0053_owner_admin_group').grant_owner_group(None, None)
        self.assertFalse(boss.groups.filter(name=OWNER_GROUP_NAME).exists())


class GroupIsIdempotentTests(TestCase):
    def test_running_the_grant_twice_is_safe(self):
        from importlib import import_module

        migration = import_module('menu.migrations.0053_owner_admin_group')
        migration.grant_owner_group(None, None)
        migration.grant_owner_group(None, None)
        self.assertEqual(Group.objects.filter(name=OWNER_GROUP_NAME).count(), 1)
