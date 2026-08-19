"""
구독·결제 화면과 웹훅.

이 파일에는 어떤 결제 대행사의 이름도, 페이로드 모양도 나오지 않는다.
그건 menu/billing/ 의 provider 가 안다. 여기가 아는 것은 구독 상태 기계뿐이다.
"""

import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .admin_views import check_restaurant_permission
from .billing import base
from .billing.base import PaymentError, PaymentNotConfigured
from .billing.registry import get_provider, get_provider_by_name
from .models import Subscription

logger = logging.getLogger(__name__)

PLAN_LABELS = dict(Subscription.PLAN_CHOICES)


def _subscription_for(restaurant):
    """
    매장의 구독 레코드.

    Restaurant post_save 가 매장마다 하나씩 만들어 주고, 그 이전에 생긴
    매장들은 마이그레이션이 partner 로 채워 두었다. 여기서 만들 일은 사실상
    없지만, 없을 때 500 을 내는 대신 미결제로 열어 두면 사장님이 결제 화면까지는
    도달한다.
    """
    subscription, _ = Subscription.objects.get_or_create(restaurant=restaurant)
    return subscription


@login_required
def billing_home(request, restaurant_slug=None):
    if not check_restaurant_permission(request.user, restaurant_slug):
        return HttpResponseForbidden("권한이 없습니다.")

    subscription = _subscription_for(request.restaurant)
    provider = get_provider()

    return render(request, 'admin/billing.html', {
        'subscription': subscription,
        'days_left': subscription.days_left,
        'access_until': subscription.access_until,
        'is_usable': subscription.is_usable(),
        # 상품명과 판매가격을 함께 넘긴다. 이름만 있는 결제 화면은
        # 전자결제 심사에서 '판매가격 미표기'로 걸린다.
        # 금액은 여기서 천단위까지 만들어 넘긴다. 템플릿의 floatformat 은
        # 구분 기호를 넣지 않아 '9900' 으로 나오고, 그건 가격표로 읽히지 않는다.
        'plans': [
            {
                'value': value,
                'label': label,
                'price': f'{Subscription.PLAN_PRICES[value]:,}',
                'current': subscription.plan == value,
            }
            for value, label in Subscription.PLAN_CHOICES
        ],
        # 결제 연동 여부를 화면에 그대로 드러낸다. 사장님이 버튼을 누르고
        # 나서야 알게 되는 것보다 낫다.
        'payment_configured': provider.name != 'null',
        'terms_url': settings.TERMS_URL,
        'contact_url': f'{settings.MARKETING_SITE_URL}/#contact',
        'support_email': settings.SUPPORT_EMAIL,
        'support_phone': settings.SUPPORT_PHONE,
    })


@login_required
@require_POST
def start_checkout(request, restaurant_slug=None):
    if not check_restaurant_permission(request.user, restaurant_slug):
        return HttpResponseForbidden("권한이 없습니다.")

    subscription = _subscription_for(request.restaurant)
    plan = request.POST.get('plan', '')
    if plan not in PLAN_LABELS:
        messages.error(request, '알 수 없는 요금제입니다.')
        return redirect('menu:billing_home', restaurant_slug=request.restaurant.slug)

    # 템플릿의 required 는 브라우저에서만 막는다. 정기결제 조건을 안내하고
    # 동의를 받았다고 말하려면 서버가 확인한 동의여야 한다.
    if request.POST.get('agree') != '1':
        messages.error(request, '정기결제 조건이 담긴 약관에 동의하셔야 결제를 진행할 수 있습니다.')
        return redirect('menu:billing_home', restaurant_slug=request.restaurant.slug)

    return_url = request.build_absolute_uri(
        reverse('menu:billing_home', kwargs={'restaurant_slug': request.restaurant.slug})
    )

    try:
        checkout_url = get_provider().start_checkout(subscription, plan, return_url)
    except PaymentNotConfigured:
        # 아직 대행사가 없다. 성공한 척하지 않고 그대로 말한다.
        messages.warning(
            request,
            f'{PLAN_LABELS[plan]} 요금제를 선택하셨습니다. 결제 연동을 준비 중이라 아직 결제가 진행되지 않으며, '
            '준비되는 대로 안내드리겠습니다.'
        )
        return redirect('menu:billing_home', restaurant_slug=request.restaurant.slug)

    return redirect(checkout_url)


@login_required
def approve_return(request, restaurant_slug=None):
    """
    결제창에서 돌아온 사용자를 받는다.

    카카오페이는 웹훅이 없다. 승인이 이 요청 안에서 일어나므로, 여기서 실패하면
    결제가 안 된 것이다. 그래서 어떤 경로로도 '성공한 척' 하지 않는다 —
    approve 가 예외를 던지면 구독은 미결제로 남는다.
    """
    if not check_restaurant_permission(request.user, restaurant_slug):
        return HttpResponseForbidden("권한이 없습니다.")

    subscription = _subscription_for(request.restaurant)
    result = request.GET.get('result', 'approve')
    home = redirect('menu:billing_home', restaurant_slug=request.restaurant.slug)

    if result == 'cancel':
        messages.info(request, '결제가 취소되었습니다. 언제든 다시 시도하실 수 있습니다.')
        return home
    if result == 'fail':
        messages.error(request, '결제에 실패했습니다. 다른 결제수단으로 다시 시도해 주세요.')
        return home

    try:
        event = get_provider().approve_return(subscription, request.GET)
    except PaymentNotConfigured as e:
        logger.warning('approve_return: 설정 없음 %s', e)
        messages.error(request, '결제 설정이 완료되지 않았습니다. 잠시 후 다시 시도해 주세요.')
        return home
    except PaymentError as e:
        # 승인 실패. 구독은 건드리지 않는다.
        logger.warning('approve_return: 승인 실패 %s', e)
        messages.error(request, f'결제를 완료하지 못했습니다. {e}')
        return home

    if _apply_event(subscription, event):
        subscription.save()
    messages.success(request, '결제가 완료되었습니다. 손님 화면이 열렸습니다.')
    return home


@login_required
@require_POST
def cancel_subscription(request, restaurant_slug=None):
    if not check_restaurant_permission(request.user, restaurant_slug):
        return HttpResponseForbidden("권한이 없습니다.")

    subscription = _subscription_for(request.restaurant)

    if subscription.status != 'canceled':
        try:
            get_provider().cancel(subscription)
        except PaymentNotConfigured:
            # 대행사가 없어도 로컬 해지는 되어야 한다. 사장님이 그만두겠다는데
            # 우리 연동 사정으로 막을 이유가 없다.
            pass
        subscription.status = 'canceled'
        subscription.canceled_at = timezone.now()
        # current_period_end 는 건드리지 않는다. 이미 낸 기간까지는 쓰는 게
        # 맞아서 access_until 을 그대로 남긴다.
        #
        # 다만 지금 Subscription.is_usable() 은 status == 'canceled' 면
        # access_until 을 보지 않고 곧바로 False 를 준다. 즉 해지 즉시 손님
        # 화면이 닫힌다. models.py 는 이 작업 범위 밖이라 고치지 못했고,
        # 보고서에 남겼다.
        subscription.save(update_fields=['status', 'canceled_at', 'updated_at'])

    messages.success(
        request,
        '구독을 해지했습니다.'
        + (f' {subscription.access_until:%Y년 %m월 %d일}까지 이용 기간이 남아 있습니다.'
           if subscription.access_until else '')
    )
    return redirect('menu:billing_home', restaurant_slug=request.restaurant.slug)


def _apply_event(subscription, event):
    """
    웹훅 사건 하나를 구독에 반영한다. 같은 사건이 두 번 와도 결과가 같아야 한다.

    중복 처리 기록용 테이블을 따로 두지 않고, 대신 모든 반영을 수렴형으로
    만들어 멱등을 얻는다. 대행사는 재전송을 밥 먹듯이 하고 순서도 뒤집어
    보내므로, '두 번째 배달을 알아채기'보다 '몇 번을 적용해도 같은 상태'가
    더 튼튼하다.

    바뀐 게 있으면 True.
    """
    if event.kind == base.EVENT_PAYMENT_SUCCEEDED:
        changed = False
        if subscription.status != 'active':
            subscription.status = 'active'
            changed = True
        if subscription.canceled_at is not None:
            subscription.canceled_at = None
            changed = True
        # 결제일은 앞으로만 민다. 늦게 도착한 지난 달 이벤트가 이용 기간을
        # 되감으면 멀쩡히 결제한 매장이 잠긴다.
        if event.period_end and (
            subscription.current_period_end is None
            or event.period_end > subscription.current_period_end
        ):
            subscription.current_period_end = event.period_end
            changed = True
        return changed

    if event.kind == base.EVENT_PAYMENT_FAILED:
        # 이미 해지된 구독을 결제 실패로 되살리지 않는다.
        if subscription.status in ('canceled', 'past_due'):
            return False
        subscription.status = 'past_due'
        return True

    if event.kind == base.EVENT_SUBSCRIPTION_CANCELED:
        if subscription.status == 'canceled':
            return False
        subscription.status = 'canceled'
        # 먼저 기록된 해지 시각을 유지한다. 재전송 때마다 갱신하면
        # '두 번 적용됐다'는 사실이 데이터에 남는다.
        if subscription.canceled_at is None:
            subscription.canceled_at = timezone.now()
        return True

    return False


@csrf_exempt
@require_POST
def webhook(request, provider):
    """
    대행사 → 우리. CSRF 토큰이 있을 리 없으니 서명으로 대신 검증한다.
    """
    adapter = get_provider_by_name(provider)
    if adapter is None:
        raise Http404("등록되지 않은 결제 대행사입니다.")

    raw_body = request.body
    if not adapter.verify_webhook(request.headers, raw_body):
        logger.warning("billing webhook signature rejected (provider=%s)", provider)
        return HttpResponseBadRequest("invalid signature")

    event = adapter.parse_webhook(raw_body)
    if event is None:
        # 우리가 관심 없는 이벤트. 4xx 를 주면 대행사가 영원히 재시도한다.
        return HttpResponse("ignored")

    subscription = Subscription.objects.filter(
        provider=provider, provider_subscription_id=event.provider_subscription_id
    ).first()
    if subscription is None:
        # 주인을 못 찾는 웹훅은 재시도해도 영원히 못 찾는다. 200 으로 끊는다.
        logger.warning(
            "billing webhook for unknown subscription (provider=%s, sub=%s)",
            provider, event.provider_subscription_id,
        )
        return HttpResponse("unknown subscription")

    if _apply_event(subscription, event):
        subscription.save()
    return HttpResponse("ok")
