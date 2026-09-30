"""
사장님 화면 사이를 잇는 링크.

메뉴 편집과 디자인은 Django admin 에 있고 주문·결제·QR 은 아직
/<slug>/admin/ 에 있다. 그 두 곳을 잇는 주소를 만들려면 '지금 누구의 매장인가'
를 알아야 하는데, /admin/ 주소에는 매장이 안 적혀 있다.

템플릿에서 request.user.profile.restaurant 를 바로 읽지 않는 이유: 프로필이
없는 슈퍼유저에게 그 표현식은 조용히 빈 값이 되고, 링크가 /admin/orders/ 처럼
매장 없는 주소로 만들어져 404 가 난다. 조용히 틀린 링크보다 아예 안 그리는
편이 낫다.
"""

from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def owner_restaurant(context):
    """지금 화면이 다루는 매장. 정할 수 없으면 None."""
    from ..admin import selected_restaurant_for

    request = context.get('request')
    if request is None or not request.user.is_authenticated:
        return None
    return selected_restaurant_for(request)


@register.simple_tag
def owner_banner_context(shop):
    """
    결제 배너가 쓰는 값들.

    커스텀 화면은 뷰가 컨텍스트를 채워 주지만 Django /admin/ 첫 화면은
    뷰가 우리 것이 아니다. 그래도 배너는 거기 떠야 한다 — 로그인 도착지가
    /admin/ 이라, 커스텀 쪽에만 넣으면 '아직 공개되지 않았습니다' 를
    사장님이 영영 보지 못한다.

    같은 _payment_banner.html 을 쓰므로 키 이름을 뷰 쪽과 맞춘다. 갈리면
    한쪽 화면에서만 배너가 조용히 사라진다.
    """
    from django.urls import reverse

    if shop is None:
        return {}
    subscription = getattr(shop, 'subscription', None)
    return {
        'menu_is_live': bool(subscription and subscription.menu_is_live()),
        'subscription': subscription,
        'billing_url': reverse('menu:billing_home', kwargs={'restaurant_slug': shop.slug}),
    }


@register.simple_tag
def owner_preview_url(shop):
    """
    공개 전 매장의 미리보기 주소. 이미 공개된 매장이면 빈 문자열.

    '손님 화면 보기' 를 그대로 두면 공개 전 매장에서 402 잠금 화면으로 간다.
    사장님이 자기 메뉴판을 확인하려고 누르는 바로 그 버튼이라, 거기서 막히면
    만들어 둔 메뉴판을 볼 방법이 없다.

    빈 문자열을 돌려주는 것으로 '미리보기가 필요한 상태인가' 까지 알린다.
    템플릿이 상태를 따로 묻지 않게 하려는 것이다 — 두 군데서 물으면 링크는
    미리보기인데 문구는 '손님 화면 보기' 인 조합이 생긴다.
    """
    from ..preview import preview_url_for

    if shop is None:
        return ''
    subscription = getattr(shop, 'subscription', None)
    if subscription is not None and subscription.menu_is_live():
        return ''
    return preview_url_for(shop)
