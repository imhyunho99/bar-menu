from django.conf import settings
from django.shortcuts import get_object_or_404, render
from django.utils.deprecation import MiddlewareMixin
from .models import Restaurant

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
    체험이 끝났거나 해지된 매장의 손님 화면을 잠근다.

    사장님 쪽(admin/) 은 절대 막지 않는다. 결제하러 들어와야 하는데 그 문까지
    잠그면 되살릴 방법이 없어진다.

    기본값은 '잠그지 않음' 이다. 결제 대행사가 아직 안 붙어서, 지금 잠그면
    체험이 끝난 사장님은 돈을 낼 방법도 없이 메뉴판만 꺼진다. 결제가 실제로
    돌기 시작하면 settings 에 ENFORCE_SUBSCRIPTION = True 를 켠다.
    RestaurantMiddleware 다음에 놓아야 request.restaurant 를 볼 수 있다.
    """

    #  사장님이 되살리러 들어오는 길. 잠금 대상에서 뺀다.
    OWNER_PREFIXES = ('admin/', 'api/v1/contact')

    def process_view(self, request, view_func, view_args, view_kwargs):
        if not getattr(settings, 'ENFORCE_SUBSCRIPTION', False):
            return None

        restaurant = getattr(request, 'restaurant', None)
        if restaurant is None:
            return None

        # /<slug>/admin/... 처럼 사장님 경로면 통과
        tail = request.path.lstrip('/')
        if tail.startswith(f'{restaurant.slug}/'):
            tail = tail[len(restaurant.slug) + 1:]
        if tail.startswith(self.OWNER_PREFIXES):
            return None

        subscription = getattr(restaurant, 'subscription', None)
        # 구독 레코드가 없는 매장은 셀프가입 이전에 손으로 만든 곳이다.
        # 소급해서 꺼버릴 이유가 없다.
        if subscription is None or subscription.is_usable():
            return None

        return render(request, 'menu/subscription_closed.html', {'restaurant': restaurant}, status=402)
