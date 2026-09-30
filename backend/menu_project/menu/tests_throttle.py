"""
레이트 리밋이 무엇을 세고 있는가.

손님 화면은 Next.js 가 **서버에서** API 를 부른다. 그래서 API 입장에서는
모든 매장의 모든 손님이 Vercel egress IP 몇 개로 보인다. 손님별로 세는 게
아니라 Vercel 을 센다 — 한도를 손님 수 기준으로 잡으면 붐비는 저녁에
정상 손님이 429 를 맞는다.

대신 주문·문의는 진짜로 조여야 한다. 그쪽은 사람이 눌러야 생기는 것이고,
쏟아지면 그게 곧 장난이다.
"""

from django.test import TestCase
from django.conf import settings


class ThrottleRatesTests(TestCase):
    def _rates(self):
        return settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']

    def test_reads_have_room_for_a_busy_night(self):
        """
        메뉴판 한 번 여는 데 요청 2개가 나간다. 분당 100 이면 전체 합쳐
        50번이고, 20명 단체 하나가 들어오면 바로 닿는다.
        """
        anon = self._rates()['anon']
        count, _, period = anon.partition('/')
        self.assertEqual(period, 'minute')
        self.assertGreaterEqual(int(count), 300, '읽기 한도가 붐비는 저녁을 못 버팁니다')

    def test_orders_are_throttled_tighter_than_reads(self):
        rates = self._rates()
        self.assertIn('orders', rates)
        self.assertLess(
            int(rates['orders'].split('/')[0]), int(rates['anon'].split('/')[0]),
            '주문이 읽기보다 헐렁하면 조이는 의미가 없습니다',
        )

    def test_contact_is_throttled_tighter_than_orders(self):
        rates = self._rates()
        self.assertIn('contact', rates)
        self.assertLess(
            int(rates['contact'].split('/')[0]), int(rates['orders'].split('/')[0]),
            '문의는 사람이 가끔 누르는 것이라 가장 좁아야 합니다',
        )


class WriteEndpointsCarryTheirOwnScopeTests(TestCase):
    """스코프를 안 붙이면 쓰기도 읽기 한도(넉넉한 쪽)를 그대로 쓴다."""

    def test_order_view_declares_its_scope(self):
        from menu.api.views import OrderCreateView

        self.assertEqual(getattr(OrderCreateView, 'throttle_scope', None), 'orders')

    def test_contact_view_declares_its_scope(self):
        from menu.api.views import ContactSubmitView

        self.assertEqual(getattr(ContactSubmitView, 'throttle_scope', None), 'contact')
