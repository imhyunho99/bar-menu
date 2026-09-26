"""
손님이 주문을 넣는 길.

앱에서 돈이 오가는 유일한 곳인데 행동 테스트가 하나도 없었다. 2026-09-25
테스트 품질 감사가 여섯 가지 변이를 넣었고 **전부 초록불로 통과했다** —
손님이 보낸 가격을 그대로 쓰기, 남의 매장 메뉴 주문, 수량 제한 제거,
합계 재계산 제거, 모든 주문을 400 으로 실패시키기, 주문 항목 버리기.

즉 모든 매장의 주문을 동시에 죽여도, 손님이 자기 가격을 정해도 묶음이
초록불이었다. 여기서 그 여섯을 막는다.

파트너 매장을 쓰는 이유: 게이트가 미결제 매장의 주문을 402 로 막으므로,
게이트가 아니라 **주문 자체**를 보려면 열린 매장이어야 한다.
"""

from django.test import TestCase
from django.test.utils import override_settings

from menu.models import Category, MenuItem, Order, OrderItem, Restaurant


@override_settings(REST_FRAMEWORK={'DEFAULT_THROTTLE_RATES': {}})
class PlacingAnOrderTests(TestCase):
    def setUp(self):
        self.shop = Restaurant.objects.create(name='달빛', slug='moonlight')
        subscription = self.shop.subscription
        subscription.status = 'partner'
        subscription.save(update_fields=['status'])

        self.category = Category.objects.create(restaurant=self.shop, name='안주')
        self.sashimi = MenuItem.objects.create(
            restaurant=self.shop, category=self.category,
            name='모둠 사시미', price='38,000',
        )
        self.beer = MenuItem.objects.create(
            restaurant=self.shop, category=self.category,
            name='생맥주', price='7000',
        )

        self.other = Restaurant.objects.create(name='남의 가게', slug='theirs')
        other_category = Category.objects.create(restaurant=self.other, name='안주')
        self.their_item = MenuItem.objects.create(
            restaurant=self.other, category=other_category,
            name='남의 메뉴', price='9000',
        )

        self.url = '/api/v1/restaurants/moonlight/orders/'

    def _post(self, payload):
        return self.client.post(self.url, payload, content_type='application/json')

    # ── 성공 경로 ────────────────────────────────────────────────────────
    def test_an_order_is_actually_created(self):
        """
        유일하게 있던 테스트는 '402 가 아니다' 만 봤다. 그래서 모든 주문을
        400 으로 실패시켜도 초록불이었다.
        """
        response = self._post({
            'table_number': '5번 테이블',
            'items': [{'menu_item': self.sashimi.id, 'quantity': 2}],
        })
        self.assertEqual(response.status_code, 201, response.content.decode())

        order = Order.objects.get(id=response.json()['order_id'])
        self.assertEqual(order.restaurant, self.shop)
        self.assertEqual(order.table_number, '5번 테이블')
        self.assertEqual(order.items.count(), 1)

        line = order.items.first()
        self.assertEqual(line.menu_item, self.sashimi)
        self.assertEqual(line.quantity, 2)

    def test_the_line_items_are_saved_not_dropped(self):
        """항목을 버려도 주문은 만들어진다 — 주방에 빈 주문이 뜬다."""
        response = self._post({
            'table_number': '3',
            'items': [
                {'menu_item': self.sashimi.id, 'quantity': 1},
                {'menu_item': self.beer.id, 'quantity': 3},
            ],
        })
        self.assertEqual(response.status_code, 201)
        order = Order.objects.get(id=response.json()['order_id'])
        self.assertEqual(
            sorted((i.menu_item_id, i.quantity) for i in order.items.all()),
            sorted([(self.sashimi.id, 1), (self.beer.id, 3)]),
        )

    # ── 돈 ──────────────────────────────────────────────────────────────
    def test_the_price_comes_from_the_database(self):
        """
        손님이 보낸 price 를 쓰면 공짜로 먹을 수 있다. 가격은 '38,000' 처럼
        글자로 저장돼 있어서, 숫자로 바꾸는 규칙까지 같이 못박는다.
        """
        response = self._post({
            'table_number': '1',
            'items': [{'menu_item': self.sashimi.id, 'quantity': 1, 'price': 1, 'name': '공짜'}],
        })
        self.assertEqual(response.status_code, 201)
        line = Order.objects.get(id=response.json()['order_id']).items.first()
        self.assertEqual(line.price, 38000, '손님이 보낸 가격이 들어갔습니다')
        self.assertEqual(line.name, '모둠 사시미', '손님이 보낸 이름이 들어갔습니다')

    def test_the_total_is_recomputed_on_the_server(self):
        response = self._post({
            'table_number': '1',
            'total_price': 10,
            'items': [
                {'menu_item': self.sashimi.id, 'quantity': 2},
                {'menu_item': self.beer.id, 'quantity': 1},
            ],
        })
        self.assertEqual(response.status_code, 201)
        order = Order.objects.get(id=response.json()['order_id'])
        self.assertEqual(order.total_price, 38000 * 2 + 7000)
        self.assertEqual(response.json()['total_price'], order.total_price)

    # ── 남의 매장 ────────────────────────────────────────────────────────
    def test_a_menu_item_from_another_store_is_refused(self):
        response = self._post({
            'table_number': '1',
            'items': [{'menu_item': self.their_item.id, 'quantity': 1}],
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Order.objects.count(), 0)

    def test_one_foreign_item_does_not_slip_in_beside_a_real_one(self):
        """섞어 보내면 앞에서 걸러도 뒤에서 통과하는 구현이 있다."""
        response = self._post({
            'table_number': '1',
            'items': [
                {'menu_item': self.sashimi.id, 'quantity': 1},
                {'menu_item': self.their_item.id, 'quantity': 1},
            ],
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(OrderItem.objects.count(), 0)

    # ── 수량 ────────────────────────────────────────────────────────────
    def test_a_quantity_above_the_limit_is_refused(self):
        response = self._post({
            'table_number': '1',
            'items': [{'menu_item': self.sashimi.id, 'quantity': 100}],
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Order.objects.count(), 0)

    def test_zero_or_negative_quantity_does_not_make_a_free_order(self):
        """음수를 받으면 합계가 깎인다. 1 로 올려 잡는 것이 지금 동작이다."""
        response = self._post({
            'table_number': '1',
            'items': [{'menu_item': self.sashimi.id, 'quantity': -5}],
        })
        self.assertEqual(response.status_code, 201)
        order = Order.objects.get(id=response.json()['order_id'])
        self.assertEqual(order.items.first().quantity, 1)
        self.assertEqual(order.total_price, 38000)

    # ── 게이트 ──────────────────────────────────────────────────────────
    def test_an_unpaid_store_cannot_take_orders(self):
        """게이트가 열려 있으면 미결제 매장이 공짜로 영업한다."""
        closed = Restaurant.objects.create(name='미결제', slug='unpaid-bar')
        category = Category.objects.create(restaurant=closed, name='안주')
        item = MenuItem.objects.create(
            restaurant=closed, category=category, name='메뉴', price='1000',
        )
        response = self.client.post(
            '/api/v1/restaurants/unpaid-bar/orders/',
            {'table_number': '1', 'items': [{'menu_item': item.id, 'quantity': 1}]},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 402)
        self.assertEqual(Order.objects.count(), 0)
