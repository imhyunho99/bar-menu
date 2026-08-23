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
