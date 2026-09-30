"""
메뉴 워크스페이스의 버튼들이 남의 매장에 닿지 않는가.

워크스페이스의 드래그정렬·복제·일괄삭제·일괄이동은 화면에서 고른 것의 **id 만**
서버로 보낸다. 그 id 가 누구 것인지 서버가 확인하지 않으면, 주소창이나
개발자도구로 id 만 바꿔 남의 매장 메뉴를 지울 수 있다. 목록에 안 보이는 것과
건드릴 수 없는 것은 다른 이야기다 — `get_queryset` 은 앞의 것만 해 준다.

2026-08-24 실측: 이 테스트들을 쓰기 전에는 A매장 사장님이 B매장 메뉴를
**삭제·복제·정렬** 할 수 있었고 전부 200 을 돌려받았다. 원래 있던 구멍인데,
로그인 도착지가 /admin/ 으로 바뀌면서 이 화면들이 모든 사장님의 일상 경로가
됐다. 운영 매장 bid·sorok 은 파트너라 특히 건드리면 안 된다.
"""

import json

from django.contrib.auth.models import Permission, User
from django.test import TestCase

from .models import Category, MenuItem, Restaurant, UserProfile


class OwnersCannotReachAnotherStoreTests(TestCase):
    def setUp(self):
        self.mine = Restaurant.objects.create(name='내 가게', slug='mine')
        self.theirs = Restaurant.objects.create(name='남의 가게', slug='theirs')

        self.their_category = Category.objects.create(
            name='남의 카테고리', restaurant=self.theirs, priority=9)
        self.their_item = MenuItem.objects.create(
            name='남의 메뉴', price=10000, restaurant=self.theirs,
            category=self.their_category, priority=9)
        self.my_item = MenuItem.objects.create(
            name='내 메뉴', price=8000, restaurant=self.mine, priority=9)

        owner = User.objects.create_user('owner@example.com', password='pw', is_staff=True)
        UserProfile.objects.create(user=owner, restaurant=self.mine, phone='050-1234-5678')
        # 권한은 넉넉히 준다. 막아야 하는 건 '권한이 없어서' 가 아니라
        # '남의 매장이라서' 이고, 둘을 헷갈리면 구멍이 그대로 남는다.
        owner.user_permissions.add(*Permission.objects.filter(content_type__app_label='menu'))
        self.client.force_login(owner)

    def _json(self, url, payload):
        return self.client.post(url, json.dumps(payload), content_type='application/json')

    # ── 정렬 ────────────────────────────────────────────────
    def test_menu_reorder_leaves_another_store_alone(self):
        self._json('/admin/menu/menuitem/reorder/', {'ids': [self.their_item.id]})
        self.their_item.refresh_from_db()
        self.assertEqual(self.their_item.priority, 9)

    def test_category_reorder_leaves_another_store_alone(self):
        self._json('/admin/menu/category/reorder/', {'ids': [self.their_category.id]})
        self.their_category.refresh_from_db()
        self.assertEqual(self.their_category.priority, 9)

    # ── 복제 ────────────────────────────────────────────────
    def test_duplicate_refuses_another_store(self):
        self.client.post(f'/admin/menu/menuitem/{self.their_item.id}/duplicate/')
        self.assertEqual(MenuItem.objects.filter(restaurant=self.theirs).count(), 1)

    def test_bulk_duplicate_refuses_another_store(self):
        self._json('/admin/menu/menuitem/bulk-duplicate/', {'ids': [self.their_item.id]})
        self.assertEqual(MenuItem.objects.filter(restaurant=self.theirs).count(), 1)

    # ── 삭제 ────────────────────────────────────────────────
    def test_bulk_delete_refuses_another_store(self):
        """가장 되돌리기 어려운 것. 여기가 뚫리면 남의 메뉴판이 사라진다."""
        self._json('/admin/menu/menuitem/bulk-delete/', {'ids': [self.their_item.id]})
        self.assertTrue(MenuItem.objects.filter(id=self.their_item.id).exists())

    def test_bulk_delete_of_a_mixed_list_spares_the_other_store(self):
        """
        내 것과 남의 것을 섞어 보내는 경우. 통째로 거절하지 않고 내 것만
        지운다 — 어느 쪽이든 남의 것이 사라지지 않는 게 지켜야 할 선이다.
        """
        self._json('/admin/menu/menuitem/bulk-delete/',
                   {'ids': [self.my_item.id, self.their_item.id]})
        self.assertTrue(MenuItem.objects.filter(id=self.their_item.id).exists())

    # ── 이동 ────────────────────────────────────────────────
    def test_bulk_move_refuses_another_stores_items(self):
        """
        고른 카테고리가 내 것인지는 이미 보고 있었다. 정작 옮기는 대상이
        누구 것인지는 안 봤다.
        """
        my_category = Category.objects.create(name='내 카테고리', restaurant=self.mine)
        self._json('/admin/menu/menuitem/bulk-move/',
                   {'ids': [self.their_item.id], 'category_id': my_category.id})
        self.their_item.refresh_from_db()
        self.assertEqual(self.their_item.category, self.their_category)

    # ── 품절 토글 ───────────────────────────────────────────
    def test_toggle_available_refuses_another_store(self):
        was = self.their_item.is_available
        self.client.post(f'/admin/menu/menuitem/{self.their_item.id}/toggle-available/')
        self.their_item.refresh_from_db()
        self.assertEqual(self.their_item.is_available, was)

    # ── 내 것은 여전히 된다 ─────────────────────────────────
    def test_my_own_store_still_works(self):
        """
        막기만 하고 끝내면 사장님이 자기 메뉴도 못 고친다. 문을 잠그는 김에
        내 문까지 잠그지 않았는지 확인한다.
        """
        self._json('/admin/menu/menuitem/reorder/', {'ids': [self.my_item.id]})
        self.my_item.refresh_from_db()
        self.assertEqual(self.my_item.priority, 0)

        self.client.post(f'/admin/menu/menuitem/{self.my_item.id}/duplicate/')
        self.assertEqual(MenuItem.objects.filter(restaurant=self.mine).count(), 2)

        self._json('/admin/menu/menuitem/bulk-delete/', {'ids': [self.my_item.id]})
        self.assertFalse(MenuItem.objects.filter(id=self.my_item.id).exists())


class SuperusersStillReachEverythingTests(TestCase):
    """매장에 매여 있지 않은 계정까지 막으면 우리가 매장을 도와줄 수 없다."""

    def setUp(self):
        self.shop = Restaurant.objects.create(name='어느 가게', slug='shop')
        self.item = MenuItem.objects.create(
            name='메뉴', price=10000, restaurant=self.shop, priority=9)
        self.client.force_login(User.objects.create_superuser('boss@example.com', password='pw'))

    def test_superuser_can_reorder_any_store(self):
        self.client.post('/admin/menu/menuitem/reorder/',
                         json.dumps({'ids': [self.item.id]}), content_type='application/json')
        self.item.refresh_from_db()
        self.assertEqual(self.item.priority, 0)
