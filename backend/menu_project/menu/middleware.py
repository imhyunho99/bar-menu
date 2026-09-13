from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils.deprecation import MiddlewareMixin
from .models import Restaurant
from .preview import PREVIEW_QUERY_PARAM, check_preview_token

class RestaurantMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        # URL 패턴에서 'restaurant_slug' 인자가 있으면 추출
        slug = view_kwargs.get('restaurant_slug')

        # 시스템 경로나 정적 파일 등은 처리하지 않음 (성능 최적화)
        if request.path.startswith(('/static/', '/media/', '/admin/', '/favicon.ico')):
            request.restaurant = None
            return None

        if slug:
            # 해당 슬러그의 Restaurant 객체를 찾아서 request에 저장
            # 없으면 404 에러 발생 (get_object_or_404)
            request.restaurant = get_object_or_404(Restaurant, slug=slug)
        else:
            request.restaurant = None

        return None


class SubscriptionGateMiddleware(MiddlewareMixin):
    """
    결제하지 않은 매장의 손님 화면을 잠근다.

    사장님 쪽(admin/) 은 절대 막지 않는다. 결제하러 들어와야 하는데 그 문까지
    잠그면 되살릴 방법이 없어진다.

    Django 가 그리는 /<slug>/ 페이지만 막아서는 아무 소용이 없다. 손님이 실제로
    보는 화면은 Vercel 의 Next.js 이고 데이터는 /api/v1/restaurants/<slug>/ 에서
    받아 간다. 그쪽 URL 인자는 restaurant_slug 가 아니라 slug 라서
    RestaurantMiddleware 가 request.restaurant 를 채우지 않으므로 여기서 직접 본다.

    2026-09 부터 기본값이 '잠금' 이다. 꺼 두면 menu_is_live() 가 무조건 True 를
    줘서 전원이 공짜가 된다. 예전에 기본 꺼짐이던 이유는 '사장님이 돈 낼 방법도
    없이 메뉴판만 꺼진다' 였는데, 계좌이체가 생기면서 전제가 바뀌었다.
    RestaurantMiddleware 다음에 놓아야 request.restaurant 를 볼 수 있다.
    """

    #  사장님이 되살리러 들어오는 길. 잠금 대상에서 뺀다.
    #
    #  qr/ 이 여기 있는 것은 'QR 은 공짜' 라는 뜻이 아니다. QR 발행은 입금
    #  확인 뒤이고, 그 판단은 qr_views 가 직접 한다. 여기서 막으면 미들웨어가
    #  손님용 '준비 중' 화면을 그리는데, QR 페이지를 보는 사람은 사장님이라
    #  무엇을 하면 열리는지 알 수 없다. 뷰까지 보내 놓고 뷰가 사장님용 안내를
    #  내도록 통과시킨다.
    OWNER_PREFIXES = ('admin/', 'qr/', 'api/v1/contact')

    API_PREFIX = '/api/v1/'

    def process_view(self, request, view_func, view_args, view_kwargs):
        if not getattr(settings, 'ENFORCE_SUBSCRIPTION', False):
            return None

        restaurant = getattr(request, 'restaurant', None)
        if restaurant is None:
            restaurant = self._restaurant_for_api(request, view_kwargs)
        if restaurant is None:
            return None

        # /<slug>/admin/... 처럼 사장님 경로면 통과
        tail = request.path.lstrip('/')
        if tail.startswith(f'{restaurant.slug}/'):
            tail = tail[len(restaurant.slug) + 1:]
        if tail.startswith(self.OWNER_PREFIXES):
            return None

        # 구독 레코드가 없으면 잠근다. 셀프가입 이전 매장을 봐주던 예외는
        # 그 매장들이 partner 구독을 갖게 되면서 필요 없어졌고, 남겨두면
        # '구독 없이 만들어진 매장은 무료' 라는 구멍이 된다. 매장이 생기는
        # 모든 경로에서 구독이 따라오도록 Restaurant post_save 가 보장한다.
        subscription = getattr(restaurant, 'subscription', None)
        if subscription is not None and subscription.is_usable():
            return None

        # 사장님이 입금 전에 자기 화면을 확인하는 통로. 구독 상태를 바꾸지
        # 않고 이 요청 하나만 통과시킨다 — 미리보기가 '결제됨' 으로 번지면
        # QR 발행까지 열린다. 워터마크는 화면 쪽이 그린다.
        if check_preview_token(restaurant.slug, request.GET.get(PREVIEW_QUERY_PARAM)):
            return None

        # 한 번도 연 적 없는 매장과 열었다 닫은 매장은 손님에게 다르게 읽혀야 한다.
        # 전자에 '잠시 후 다시' 라고 하면 열릴 리 없는 화면을 계속 새로고침한다.
        never_opened = subscription is None or subscription.status == 'unpaid'

        if request.path.startswith(self.API_PREFIX):
            # HTML 을 기대하지 않는 쪽이다. 프론트가 status 로 갈래를 타도록
            # 같은 402 에 기계가 읽을 수 있는 이유를 붙여 준다.
            return JsonResponse(
                {
                    'detail': '이 매장의 메뉴판은 아직 열려 있지 않습니다.',
                    'reason': 'never_opened' if never_opened else 'closed',
                    'restaurant': restaurant.name,
                },
                status=402,
            )

        return render(
            request,
            'menu/subscription_closed.html',
            {'restaurant': restaurant, 'never_opened': never_opened},
            status=402,
        )

    def _restaurant_for_api(self, request, view_kwargs):
        """
        /api/v1/restaurants/<slug>/... 의 매장.

        같은 이름 slug 를 쓰는 다른 API 가 나중에 생겨도 오작동하지 않도록
        경로 접두사를 함께 본다. 매장에 딸리지 않은 /api/v1/contact/ 같은
        경로는 slug 가 없으니 자연히 빠진다.
        """
        if not request.path.startswith(self.API_PREFIX):
            return None
        slug = view_kwargs.get('slug')
        if not slug:
            return None
        # 구독을 같이 끌어온다. 바로 아래에서 is_usable() 을 부르므로 따로
        # 두면 손님 요청마다 쿼리가 한 번 더 나간다.
        return Restaurant.objects.filter(slug=slug).select_related('subscription').first()
