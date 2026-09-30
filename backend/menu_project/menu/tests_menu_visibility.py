"""
사장님이 등록한 메뉴가 손님에게 실제로 보이는가.

손님 화면은 카테고리를 타고 그려진다. 카테고리 없는 메뉴는 DB 에 있어도
어디에도 나타나지 않는다. 그런데 온보딩 체크리스트는 메뉴 개수만 세어
'메뉴 등록 완료'로 표시한다. 그 둘이 어긋나면 사장님은 다 했다고 믿고
QR 을 인쇄해 테이블에 붙인 뒤, 개업 당일에 빈 메뉴판을 보게 된다.

사진으로 등록하는 경로는 이미 카테고리를 만들어 담는다('메뉴'). 직접 입력도
같아야 한다.
"""

from django.contrib.auth.models import User
from django.test import TestCase

from .models import Category, MenuItem, Restaurant, UserProfile

DEFAULT_CATEGORY_NAME = '메뉴'


class MenuAlwaysLandsInACategoryTests(TestCase):
    def setUp(self):
        self.restaurant = Restaurant.objects.create(name="달빛 이자카야", slug="moonlight")
        self.owner = User.objects.create_user(username='owner', password='pw', is_staff=True)
        UserProfile.objects.create(user=self.owner, restaurant=self.restaurant)
        self.client.force_login(self.owner)

    def _add(self, **overrides):
        payload = {'name': '라프로익 10년', 'price': '18,000', 'description': ''}
        payload.update(overrides)
        return self.client.post('/moonlight/admin/menu/add/', payload)

    def test_first_menu_without_a_category_still_becomes_visible(self):
        """갓 가입한 매장에는 카테고리가 없다. 그래도 등록한 메뉴는 보여야 한다."""
        self._add()

        item = MenuItem.objects.get(restaurant=self.restaurant)
        self.assertIsNotNone(item.category, '카테고리 없는 메뉴는 손님 화면에 나타나지 않는다')
        self.assertEqual(item.category.name, DEFAULT_CATEGORY_NAME)

    def test_the_default_category_is_reused_not_duplicated(self):
        self._add()
        self._add(name='아드벡 10년')

        self.assertEqual(
            Category.objects.filter(restaurant=self.restaurant, name=DEFAULT_CATEGORY_NAME).count(), 1
        )

    def test_an_explicit_category_is_respected(self):
        whisky = Category.objects.create(name='위스키', restaurant=self.restaurant)
        self._add(category=whisky.id)

        self.assertEqual(MenuItem.objects.get(restaurant=self.restaurant).category, whisky)
        self.assertFalse(
            Category.objects.filter(restaurant=self.restaurant, name=DEFAULT_CATEGORY_NAME).exists(),
            '고른 카테고리가 있는데 기본 카테고리를 만들 이유가 없다',
        )

    def test_the_default_category_belongs_to_this_restaurant_only(self):
        other = Restaurant.objects.create(name='남의 가게', slug='other')
        Category.objects.create(name=DEFAULT_CATEGORY_NAME, restaurant=other)

        self._add()

        item = MenuItem.objects.get(restaurant=self.restaurant)
        self.assertEqual(item.category.restaurant, self.restaurant)


class OnboardingReflectsWhatCustomersSeeTests(TestCase):
    """체크 표시는 손님 화면 기준이어야 한다."""

    def setUp(self):
        self.restaurant = Restaurant.objects.create(name="달빛 이자카야", slug="moonlight")
        self.owner = User.objects.create_user(username='owner', password='pw', is_staff=True)
        UserProfile.objects.create(user=self.owner, restaurant=self.restaurant)
        self.client.force_login(self.owner)

    def test_menu_step_counts_only_menus_customers_can_reach(self):
        MenuItem.objects.create(
            name='숨은 메뉴', price='1,000', description='',
            category=None, restaurant=self.restaurant,
        )

        response = self.client.get('/moonlight/admin/start/')
        steps = {step['key']: step for step in response.context['steps']}
        self.assertFalse(
            steps['menu']['done'],
            '손님이 볼 수 없는 메뉴를 등록 완료로 표시하면 개업 당일에 사고가 난다',
        )
