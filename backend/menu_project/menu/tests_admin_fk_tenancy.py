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


class ACategoryCannotBeItsOwnParentTests(TestCase):
    """
    매장 안으로 좁혀도 A.parent = A 는 남는다. 하위 목록을 재귀로 따라가는
    곳이 있어 거기서 무한으로 돈다 — 테넌시 버그를 재귀 버그로 바꾸는 꼴이다.
    커스텀 화면(admin_views.py)은 이미 자기 자신을 빼고 있었다.
    """

    def setUp(self):
        self.shop = Restaurant.objects.create(name='내 가게', slug='mine')
        self.category = Category.objects.create(restaurant=self.shop, name='안주')
        self.owner = User.objects.create_user('me@example.com', password='pw-91827', is_staff=True)
        UserProfile.objects.create(user=self.owner, restaurant=self.shop)
        from django.contrib.auth.models import Group
        group = Group.objects.filter(name__icontains='사장').first()
        if group:
            self.owner.groups.add(group)
        self.client.force_login(self.owner)

    def test_the_parent_dropdown_excludes_the_row_being_edited(self):
        response = self.client.get(f'/admin/menu/category/{self.category.pk}/change/')
        if response.status_code != 200:
            self.skipTest('이 계정은 변경 화면에 못 들어간다')
        choices = response.context['adminform'].form.fields['parent'].queryset
        self.assertNotIn(self.category, choices)

    def test_a_forged_post_cannot_make_it_its_own_parent(self):
        response = self.client.post(f'/admin/menu/category/{self.category.pk}/change/', {
            'name': '안주', 'parent': self.category.pk, 'priority': '1',
        })
        self.category.refresh_from_db()
        self.assertIsNone(self.category.parent, f'자기 자신이 부모가 됐습니다 (HTTP {response.status_code})')


class AStrayForeignKeyChangesNothingForCustomersTests(TestCase):
    """
    폼 가드가 못 닿는 길이 남아 있다 — ORM, import_csv, 픽스처, 앞으로 생길
    API. 그쪽으로 침입 FK 가 들어오더라도 손님 화면에는 아무 일이 없어야
    한다. 여기서는 일부러 ORM 으로 심어서 확인한다.

    막지 않으면 피해가 두 겹이다. 남의 글자가 하위 카테고리로 뜨고, 하위가
    생겼다는 이유로 원래 메뉴가 통째로 사라진다.
    """

    def setUp(self):
        self.victim = Restaurant.objects.create(name='피해 가게', slug='victim')
        self.attacker = Restaurant.objects.create(name='공격 가게', slug='attacker')
        sub = self.victim.subscription
        sub.status = 'partner'
        sub.save(update_fields=['status'])

        self.category = Category.objects.create(restaurant=self.victim, name='안주')
        MenuItem.objects.create(
            restaurant=self.victim, category=self.category, name='진짜 메뉴', price='10000',
        )
        # 폼을 거치지 않고 심는다.
        Category.objects.create(
            restaurant=self.attacker, name='ZZ 남의 글자', parent=self.category,
        )

    def test_the_api_hides_it_and_keeps_the_menu(self):
        response = self.client.get(f'/api/v1/restaurants/victim/categories/{self.category.pk}/')
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['sub_categories'], [], '남의 카테고리가 손님에게 보입니다')
        self.assertEqual([m['name'] for m in body['menu_items']], ['진짜 메뉴'])

    def test_the_server_rendered_page_hides_it_too(self):
        """serializer 만 고치면 Django 가 그리는 쪽이 그대로 뚫려 있다."""
        response = self.client.get(f'/victim/category/{self.category.pk}/')
        self.assertEqual(response.status_code, 200)
        html = response.content.decode('utf-8')
        self.assertNotIn('ZZ 남의 글자', html)
        self.assertIn('진짜 메뉴', html)
