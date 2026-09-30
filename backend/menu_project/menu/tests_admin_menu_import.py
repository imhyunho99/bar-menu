"""
메뉴판 사진 등록이 Django admin 안에서도 되는가.

사진 등록은 /<slug>/admin/ 에만 있었고 디자인 도구는 /admin/ 에만 있었다.
사장님은 메뉴를 손보다가 사진을 올리려고 다른 주소로 넘어가야 했고, 그 주소는
자기 매장 slug 를 외워야 닿는 곳이다. 그래서 사진 등록을 /admin/ 쪽으로도 낸다.

주소에 매장이 안 드러나는 게 이 경로의 핵심 차이다. slug 가 없으니 '누구의
매장인가' 를 계정에서 읽어야 하고, 그 판단이 틀리면 남의 매장 메뉴판이
우리에게 날아온다. 아래 테스트가 지키는 건 대부분 그 지점이다.
"""

import io
from unittest import mock

from django.contrib.auth.models import Permission, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image

from .models import Restaurant, UserProfile

ADMIN_IMPORT_URL = '/admin/menu/menuitem/import/'
WORKSPACE_URL = '/admin/menu/menuitem/'
SIGNUP_URL = '/signup/'


def photo(name='menu.jpg', size=(1200, 900)):
    buf = io.BytesIO()
    Image.new('RGB', size, (200, 180, 160)).save(buf, 'JPEG', quality=85)
    return SimpleUploadedFile(name, buf.getvalue(), content_type='image/jpeg')


class OwnerImportsPhotosInsideDjangoAdminTests(TestCase):
    def setUp(self):
        self.client.post(SIGNUP_URL, {
            'email': 'owner@example.com',
            'password': 'jazz-bar-9137',
            'name': '달빛 이자카야',
            'slug': 'moonlight',
        })
        self.owner = User.objects.get(username='owner@example.com')
        self.restaurant = self.owner.profile.restaurant
        self.client.force_login(self.owner)

    def _post(self, n=1):
        return self.client.post(
            ADMIN_IMPORT_URL,
            {'menu_image': [photo(f'p{i}.jpg') for i in range(n)]},
            follow=True,
        )

    def test_owner_reaches_the_page(self):
        """슬러그를 모르는 채로도 닿아야 한다. 그게 이 주소를 만든 이유다."""
        self.assertEqual(self.client.get(ADMIN_IMPORT_URL).status_code, 200)

    def test_photos_go_out_under_the_owners_own_restaurant(self):
        """
        주소에 매장이 없으니 매장은 계정에서 읽는다. 여기가 틀리면 사진은
        가는데 엉뚱한 매장 이름을 달고 간다 — 아무도 오류로 눈치채지 못한다.
        """
        with mock.patch('menu.notifications.send_menu_photos', return_value=True) as send:
            self._post(2)
        send.assert_called_once()
        self.assertEqual(send.call_args.args[0], self.restaurant)
        self.assertEqual(len(send.call_args.args[1]), 2)

    def test_success_returns_to_the_menu_workspace(self):
        """
        보내고 나면 하던 일로 돌아가야 한다. 커스텀 대시보드로 튕기면
        한 곳에서 다 되게 만든 의미가 없어진다.
        """
        with mock.patch('menu.notifications.send_menu_photos', return_value=True):
            response = self._post(1)
        self.assertEqual(response.redirect_chain[-1][0], WORKSPACE_URL)

    def test_failure_to_send_is_not_reported_as_success(self):
        with mock.patch('menu.notifications.send_menu_photos', return_value=False):
            response = self._post(1)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.redirect_chain, [])
        self.assertContains(response, '보내지 못했습니다')

    def test_the_workspace_links_to_the_page(self):
        """문을 만들어 놓고 손잡이를 안 달면 아무도 못 연다."""
        self.assertContains(self.client.get(WORKSPACE_URL), ADMIN_IMPORT_URL)


class StrangersCannotUseItTests(TestCase):
    def setUp(self):
        self.restaurant = Restaurant.objects.create(name='달빛', slug='moonlight')

    def test_anonymous_is_sent_to_the_login_page(self):
        response = self.client.get(ADMIN_IMPORT_URL)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response['Location'])

    def test_staff_without_a_restaurant_is_refused(self):
        """
        매장이 안 딸린 스태프 계정이 존재한다. 여기서 조용히 첫 매장을 집으면
        남의 매장 메뉴판이 우리에게 날아온다.
        """
        stray = User.objects.create_user('stray@example.com', password='pw', is_staff=True)
        self.client.force_login(stray)
        with mock.patch('menu.notifications.send_menu_photos', return_value=True) as send:
            response = self.client.post(ADMIN_IMPORT_URL, {'menu_image': [photo()]})
        self.assertEqual(response.status_code, 403)
        send.assert_not_called()


class SuperuserPicksTheRestaurantTests(TestCase):
    def setUp(self):
        self.first = Restaurant.objects.create(name='가나다', slug='aaa')
        self.second = Restaurant.objects.create(name='하하하', slug='zzz')
        boss = User.objects.create_superuser('boss@example.com', password='pw')
        self.client.force_login(boss)

    def test_superuser_sends_for_the_restaurant_they_chose(self):
        """
        메뉴 워크스페이스가 이미 ?restaurant=<id> 로 매장을 고른다. 같은 화면
        안의 버튼이 다른 규칙을 쓰면 고른 매장과 사진 가는 매장이 어긋난다.
        """
        with mock.patch('menu.notifications.send_menu_photos', return_value=True) as send:
            self.client.post(
                f'{ADMIN_IMPORT_URL}?restaurant={self.second.id}',
                {'menu_image': [photo()]},
                follow=True,
            )
        self.assertEqual(send.call_args.args[0], self.second)

    def test_superuser_without_a_choice_gets_the_first_restaurant(self):
        with mock.patch('menu.notifications.send_menu_photos', return_value=True) as send:
            self.client.post(ADMIN_IMPORT_URL, {'menu_image': [photo()]}, follow=True)
        self.assertEqual(send.call_args.args[0], self.first)


class TheSlugRouteStillWorksTests(TestCase):
    """
    옛 주소를 지우지 않는다. 커스텀 대시보드가 아직 그 버튼을 들고 있어서,
    지우면 사장님이 절반은 새 화면 절반은 깨진 링크를 보게 된다.
    """

    def setUp(self):
        self.restaurant = Restaurant.objects.create(name='달빛', slug='moonlight')
        owner = User.objects.create_user('owner@example.com', password='pw', is_staff=True)
        UserProfile.objects.create(user=owner, restaurant=self.restaurant, phone='050-1234-5678')
        self.client.force_login(owner)

    def test_the_old_address_still_sends(self):
        with mock.patch('menu.notifications.send_menu_photos', return_value=True) as send:
            self.client.post('/moonlight/admin/menu/import/', {'menu_image': [photo()]}, follow=True)
        self.assertEqual(send.call_args.args[0], self.restaurant)


class TheRestaurantPickerHoldsUnderJunkTests(TestCase):
    """
    매장을 고르는 규칙(admin.selected_restaurant_for)은 이제 세 화면이 함께
    쓴다 — /admin/ 첫 화면, 메뉴 워크스페이스, 사진 등록. 한 군데서 터지면
    셋 다 터지고, 그중 하나는 로그인하면 바로 도착하는 화면이다.
    """

    def setUp(self):
        self.mine = Restaurant.objects.create(name='내 가게', slug='mine')
        self.theirs = Restaurant.objects.create(name='남의 가게', slug='theirs')
        owner = User.objects.create_user('owner@example.com', password='pw', is_staff=True)
        UserProfile.objects.create(user=owner, restaurant=self.mine, phone='050-1234-5678')
        self.owner = owner

    def test_owner_cannot_send_under_another_restaurant(self):
        """
        사장님은 ?restaurant= 를 아예 보지 않는다. 지금도 그렇지만, 슈퍼유저
        분기 조건을 누가 느슨하게 바꾸면 남의 매장 메뉴판이 우리에게 날아오고
        화면에는 아무 표시도 남지 않는다. 그 순간 울릴 것이 필요하다.
        """
        self.client.force_login(self.owner)
        with mock.patch('menu.notifications.send_menu_photos', return_value=True) as send:
            self.client.post(
                f'{ADMIN_IMPORT_URL}?restaurant={self.theirs.id}',
                {'menu_image': [photo()]},
                follow=True,
            )
        send.assert_called_once()
        self.assertEqual(send.call_args.args[0], self.mine)

    def test_junk_in_the_query_string_does_not_500(self):
        """
        주소창을 손으로 고치면 나는 에러다. 슈퍼유저 전용이라 위험하진 않지만,
        로그인 도착지가 /admin/ 이 된 뒤로는 첫 화면이 통째로 죽는다.
        """
        boss = User.objects.create_superuser('boss@example.com', password='pw')
        self.client.force_login(boss)
        for url in ('/admin/?restaurant=abc',
                    '/admin/menu/menuitem/?restaurant=abc',
                    f'{ADMIN_IMPORT_URL}?restaurant=abc'):
            with self.subTest(url=url):
                # 워크스페이스는 Django 가 잘못된 필터값을 ?e=1 로 되돌린다.
                # 그건 설계된 동작이라 그대로 두고, 도착한 화면만 본다.
                self.assertEqual(self.client.get(url, follow=True).status_code, 200)

    def test_the_photo_button_is_hidden_when_there_is_no_restaurant(self):
        """
        매장이 안 묶인 스태프에게는 눌러야 403 이 나오는 죽은 버튼이 된다.
        누르기 전에 없는 편이 낫다.
        """
        stray = User.objects.create_user('stray@example.com', password='pw', is_staff=True)
        stray.user_permissions.add(*Permission.objects.filter(
            content_type__app_label='menu', codename__in=['view_menuitem', 'change_menuitem']))
        self.client.force_login(stray)
        self.assertNotContains(self.client.get(WORKSPACE_URL), ADMIN_IMPORT_URL)
