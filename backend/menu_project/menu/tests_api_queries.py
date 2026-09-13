"""
손님 화면이 부르는 API 가 쿼리를 몇 번 내는가.

손님이 메뉴판을 열 때마다 layout 이 매장 상세와 카테고리 트리를 부른다.
쿼리 수가 카테고리 수를 따라 늘면, 메뉴가 많은 가게일수록 느려지고
워커가 오래 잡힌다 — 트래픽이 몰릴 때 가장 먼저 무너지는 자리다.

이 파일은 '빠른가' 가 아니라 '건수가 데이터 양을 따라가지 않는가' 를 본다.
시간은 기계마다 다르지만 쿼리 수는 그렇지 않다.
"""

from django.test import TestCase, override_settings

from menu.models import Category, Restaurant


@override_settings(ENFORCE_SUBSCRIPTION=False)
class CategoryTreeQueryCountTests(TestCase):
    def setUp(self):
        self.restaurant = Restaurant.objects.create(name='쿼리 바', slug='query-bar')
        self.url = '/api/v1/restaurants/query-bar/category-tree/'

    def _tree(self, breadth, depth):
        """breadth 갈래 × depth 층짜리 카테고리 트리를 만든다."""
        level = [None]
        for _ in range(depth):
            nxt = []
            for parent in level:
                for i in range(breadth):
                    nxt.append(Category.objects.create(
                        name=f'c{len(nxt)}-{i}', parent=parent, restaurant=self.restaurant,
                    ))
            level = nxt

    def test_query_count_does_not_grow_with_the_tree(self):
        """
        예전에는 카테고리마다 한 번씩 나갔다. 직렬화기의 .order_by() 가
        prefetch 캐시를 버리기 때문인데, 그 사실이 코드 어디에도 안 보인다.
        """
        self._tree(breadth=2, depth=2)          # 6개
        with self.assertNumQueries(2):
            self.client.get(self.url)

        Category.objects.filter(restaurant=self.restaurant).delete()
        self._tree(breadth=4, depth=3)          # 84개
        with self.assertNumQueries(2):
            self.client.get(self.url)

    def test_the_tree_is_still_nested_correctly(self):
        top = Category.objects.create(name='주류', priority=1, restaurant=self.restaurant)
        mid = Category.objects.create(name='위스키', parent=top, priority=1, restaurant=self.restaurant)
        Category.objects.create(name='싱글몰트', parent=mid, priority=1, restaurant=self.restaurant)

        data = self.client.get(self.url).json()

        self.assertEqual([c['name'] for c in data], ['주류'])
        self.assertEqual([c['name'] for c in data[0]['sub_categories']], ['위스키'])
        self.assertEqual(
            [c['name'] for c in data[0]['sub_categories'][0]['sub_categories']],
            ['싱글몰트'],
        )

    def test_children_keep_their_order(self):
        top = Category.objects.create(name='안주', priority=1, restaurant=self.restaurant)
        Category.objects.create(name='나중', parent=top, priority=9, restaurant=self.restaurant)
        Category.objects.create(name='먼저', parent=top, priority=1, restaurant=self.restaurant)

        data = self.client.get(self.url).json()
        self.assertEqual([c['name'] for c in data[0]['sub_categories']], ['먼저', '나중'])

    def test_another_restaurants_categories_never_appear(self):
        other = Restaurant.objects.create(name='남의 바', slug='other-bar')
        Category.objects.create(name='남의 카테고리', restaurant=other)
        Category.objects.create(name='우리 카테고리', restaurant=self.restaurant)

        data = self.client.get(self.url).json()
        self.assertEqual([c['name'] for c in data], ['우리 카테고리'])


class RestaurantDetailQueryCountTests(TestCase):
    def setUp(self):
        self.restaurant = Restaurant.objects.create(name='쿼리 바', slug='query-bar')
        self.url = '/api/v1/restaurants/query-bar/'
        self.restaurant.subscription.status = 'partner'
        self.restaurant.subscription.save(update_fields=['status'])

    @override_settings(ENFORCE_SUBSCRIPTION=False)
    def test_detail_stays_at_a_fixed_query_count(self):
        """
        메뉴가 늘어도 매장 상세는 같은 건수여야 한다. 여기가 늘면 큰 가게일수록
        손님 화면 첫 응답이 느려진다.
        """
        with self.assertNumQueries(2):
            self.client.get(self.url)

        for i in range(30):
            Category.objects.create(name=f'c{i}', restaurant=self.restaurant)

        with self.assertNumQueries(2):
            self.client.get(self.url)

    @override_settings(ENFORCE_SUBSCRIPTION=True)
    def test_the_gate_does_not_add_a_query_per_request(self):
        """
        운영은 게이트를 켜고 돈다. 미들웨어가 매장과 구독을 따로 읽으면
        손님 요청마다 쿼리가 한 번씩 더 붙는다 — select_related 로 묶어
        게이트가 쓰는 건 한 번이다.

        게이트 없을 때보다 하나 많은 것은 미들웨어와 뷰가 각자 매장을 읽기
        때문이다. 없애려면 미들웨어가 읽은 것을 뷰가 물려받아야 하는데,
        그 결합을 만들 만큼 비싸지는 않다.
        """
        with self.assertNumQueries(3):
            self.client.get(self.url)
