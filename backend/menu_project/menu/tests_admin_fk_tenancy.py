"""
남의 매장 행을 가리키는 칸을 만들 수 있는가.

`RestaurantFilterMixin.save_model` 은 obj.restaurant 만 바로잡는다. 가리키는
**상대**는 안 본다. 2026-09-25 적대적 검토가 그 틈으로 카테고리의 parent 에
남의 매장 카테고리를 붙였다.

피해가 두 겹이다. 남의 손님 화면에 내가 쓴 글자가 하위 카테고리로 뜨고,
원래 있던 **메뉴가 통째로 사라진다** — 하위가 생기면 serializer 가 메뉴 대신
하위 목록을 준다. 영업 중에 당하면 사장님은 이유를 모른다.

드롭다운만 좁히는 것으로는 부족하다. 화면에 없던 id 를 손으로 밀어 넣는
POST 까지 막혀야 한다.
"""

from django.contrib.auth.models import User
from django.test import TestCase

from menu.models import Category, MenuItem, Restaurant, UserProfile


class ForeignKeyChoicesStayInsideTheStoreTests(TestCase):
    def setUp(self):
        self.mine = Restaurant.objects.create(name='내 가게', slug='mine')
        self.theirs = Restaurant.objects.create(name='남의 가게', slug='theirs')

        self.my_category = Category.objects.create(restaurant=self.mine, name='내 안주')
        self.their_category = Category.objects.create(restaurant=self.theirs, name='남의 안주')
        MenuItem.objects.create(
            restaurant=self.theirs, category=self.their_category,
            name='남의 메뉴', price='10000',
        )

        self.owner = User.objects.create_user('me@example.com', password='pw-91827', is_staff=True)
        UserProfile.objects.create(user=self.owner, restaurant=self.mine)
        from django.contrib.auth.models import Group
        group = Group.objects.filter(name__icontains='사장').first()
        if group:
            self.owner.groups.add(group)
        else:  # 그룹이 없으면 필요한 권한만 직접 준다
            from django.contrib.auth.models import Permission
            for code in ('add_category', 'change_category', 'view_category'):
                perm = Permission.objects.filter(codename=code).first()
                if perm:
                    self.owner.user_permissions.add(perm)
        self.client.force_login(self.owner)

    def test_the_parent_dropdown_shows_only_my_own_categories(self):
        response = self.client.get('/admin/menu/category/add/')
        self.assertEqual(response.status_code, 200)
        choices = response.context['adminform'].form.fields['parent'].queryset
        self.assertIn(self.my_category, choices)
        self.assertNotIn(self.their_category, choices, '남의 매장 카테고리가 보입니다')

    def test_a_forged_post_cannot_attach_to_another_store(self):
        """
        드롭다운만 좁히면 렌더링만 막힌다. ModelChoiceField 가 검증할 때도
        같은 queryset 으로 거르는지를 본다 — 여기가 진짜 방어선이다.
        """
        response = self.client.post('/admin/menu/category/add/', {
            'name': 'ZZ 침입',
            'parent': self.their_category.pk,
            'priority': '1',
        })
        self.assertEqual(response.status_code, 200, '저장됐습니다(302)')
        self.assertFalse(
            Category.objects.filter(parent=self.their_category).exists(),
            '남의 카테고리 밑에 붙었습니다',
        )

    def test_the_victims_menu_does_not_disappear(self):
        """피해의 본체. 하위가 생기면 그 카테고리의 메뉴가 손님에게 안 보인다."""
        self.client.post('/admin/menu/category/add/', {
            'name': 'ZZ 침입', 'parent': self.their_category.pk, 'priority': '1',
        })
        self.assertEqual(self.their_category.sub_categories.count(), 0)
        self.assertEqual(MenuItem.objects.filter(category=self.their_category).count(), 1)

    def test_a_staff_account_without_a_store_gets_no_choices(self):
        """매장이 안 묶인 스태프 계정이 실제로 있다. 열어 두면 아무거나 고른다."""
        stray = User.objects.create_user('stray@example.com', password='pw-55512', is_staff=True)
        from django.contrib.auth.models import Group
        group = Group.objects.filter(name__icontains='사장').first()
        if group:
            stray.groups.add(group)
        self.client.force_login(stray)
        response = self.client.get('/admin/menu/category/add/')
        if response.status_code != 200:
            self.skipTest('이 계정은 화면 자체에 못 들어간다')
        self.assertEqual(response.context['adminform'].form.fields['parent'].queryset.count(), 0)

    def test_a_superuser_still_sees_everything(self):
        """막는 것이 목적이지, 지원하러 들어간 사람을 묶는 것이 아니다."""
        boss = User.objects.create_superuser('boss', 'b@x.test', 'pw-33129')
        self.client.force_login(boss)
        response = self.client.get('/admin/menu/category/add/')
        choices = response.context['adminform'].form.fields['parent'].queryset
        self.assertIn(self.my_category, choices)
        self.assertIn(self.their_category, choices)
