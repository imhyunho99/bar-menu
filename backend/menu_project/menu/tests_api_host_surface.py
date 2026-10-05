"""
api.* 호스트가 내보이는 것.

이 호스트에는 **손님 화면이 없다.** 2026-07 에 손님 화면을 Next.js 로 옮겼는데
Django 가 그리던 옛 화면들이 그대로 살아 있었고, 2026-10-05 실측에서 이렇게
나왔다.

    GET https://api.bar-menu.ddnsfree.com/     200, 30KB
      → 등록된 모든 매장을 나열하는 옛 랜딩 (bid, sorok, test 가 그대로 보였다)
    GET /bid/   /sorok/   /test/              전부 200
      → 손님 사이트와 똑같은 메뉴판이 두 주소에 떠 있었다

피해가 셋이었다. 고객사 목록이 공개됐고, 옛 홍보 문구가 진짜 랜딩과 중복으로
색인됐고, 봇이 이쪽을 긁다가 2026-10-02 staticfiles 500 이 쏟아졌다.

여기서 고정하는 것: 루트는 매장을 나열하지 않는다, 레거시 메뉴 주소는 손님
사이트로 넘어간다, 봇에게는 긁지 말라고 말한다.
"""

from django.test import TestCase, override_settings

from menu.models import Category, Restaurant

CUSTOMER = 'https://customer.example.com'


@override_settings(CUSTOMER_SITE_URL=CUSTOMER)
class TheRootDoesNotListTenantsTests(TestCase):
    def setUp(self):
        Restaurant.objects.create(name='첫째 가게', slug='first-bar')
        Restaurant.objects.create(name='둘째 가게', slug='second-bar')

    def test_the_root_redirects_to_the_customer_site(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], f'{CUSTOMER}/')

    def test_the_root_never_renders_a_store_list(self):
        """
        리다이렉트가 아니라 **목록이 안 나오는 것**이 요점이다. 나중에 누가
        여기에 다시 페이지를 붙이더라도 이 테스트가 매장 이름을 잡는다.
        """
        response = self.client.get('/', follow=False)
        body = response.content.decode(errors='replace')
        for leaked in ('first-bar', 'second-bar', '첫째 가게', '둘째 가게'):
            self.assertNotIn(leaked, body, f'루트 응답에 {leaked} 가 들어 있습니다')

    @override_settings(CUSTOMER_SITE_URL='')
    def test_without_a_customer_site_it_still_does_not_list_stores(self):
        """설정이 비어도 '그러면 옛 목록을 보여주자'로 떨어지면 안 된다."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 404)
        body = response.content.decode(errors='replace')
        self.assertNotIn('first-bar', body)


@override_settings(CUSTOMER_SITE_URL=CUSTOMER)
class LegacyCustomerPagesMoveToTheCustomerSiteTests(TestCase):
    def setUp(self):
        self.restaurant = Restaurant.objects.create(name='옛 가게', slug='legacy-bar')
        self.restaurant.subscription.status = 'partner'
        self.restaurant.subscription.save(update_fields=['status'])
        self.category = Category.objects.create(restaurant=self.restaurant, name='안주')

    def test_the_menu_page_redirects(self):
        """
        301 이지 404 가 아니다. 인쇄된 옛 QR 이 이 주소를 가리키고 있을 수
        있고, 종이는 다시 못 찍는다.
        """
        response = self.client.get('/legacy-bar/')
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], f'{CUSTOMER}/legacy-bar')

    def test_the_category_page_redirects_to_the_same_category(self):
        response = self.client.get(f'/legacy-bar/category/{self.category.id}/')
        self.assertEqual(response.status_code, 301)
        self.assertEqual(
            response['Location'], f'{CUSTOMER}/legacy-bar/category/{self.category.id}',
        )

    def test_the_owner_surfaces_are_untouched(self):
        """
        넘기는 것은 손님 화면뿐이다. 주문·결제·QR 은 아직 여기 있다 —
        같이 넘기면 사장님이 쓰던 화면이 통째로 사라진다.
        """
        for path in ('/legacy-bar/admin/login/', '/legacy-bar/qr/'):
            response = self.client.get(path)
            self.assertNotEqual(
                response.status_code, 301,
                f'{path} 까지 손님 사이트로 넘어갔습니다',
            )


class BotsAreToldNotToCrawlTests(TestCase):
    def test_robots_disallows_everything(self):
        response = self.client.get('/robots.txt')
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn('User-agent: *', body)
        self.assertIn('Disallow: /', body)
