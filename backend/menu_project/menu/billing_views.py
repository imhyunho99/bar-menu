"""
구독·결제 화면과 웹훅.

이 파일에는 어떤 결제 대행사의 이름도, 페이로드 모양도 나오지 않는다.
그건 menu/billing/ 의 provider 가 안다. 여기가 아는 것은 구독 상태 기계뿐이다.
"""

import logging

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
from .billing.base import PaymentNotConfigured
from .billing.registry import get_provider, get_provider_by_name
from .models import Subscription

logger = logging.getLogger(__name__)

PLAN_LABELS = dict(Subscription.PLAN_CHOICES)


def _subscription_for(restaurant):
    """
    매장의 구독 레코드. 셀프가입 이전에 만들어진 매장은 아직 없으므로 만들어 준다.

    이때 체험을 시작해 주는 건 의도적이다. 없는 구독을 canceled 로 만들어
    두면 기존 매장의 메뉴판이 어느 날 갑자기 꺼진다.
    """
    subscription, created = Subscription.objects.get_or_create(restaurant=restaurant)
    if created:
        subscription.start_trial()
        subscription.save()
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
        'plans': Subscription.PLAN_CHOICES,
        # 결제 연동 여부를 화면에 그대로 드러낸다. 사장님이 버튼을 누르고
        # 나서야 알게 되는 것보다 낫다.
        'payment_configured': provider.name != 'null',
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

    return_url = request.build_absolute_uri(
        reverse('menu:billing_home', kwargs={'restaurant_slug': request.restaurant.slug})
    )

    try:
        checkout_url = get_provider().start_checkout(subscription, plan, return_url)
    except PaymentNotConfigured:
        # 아직 대행사가 없다. 성공한 척하지 않고 그대로 말한다.
        messages.warning(
            request,
            f'아직 결제 연동 전입니다. {PLAN_LABELS[plan]} 요금제 신청은 담당자에게 문의해 주세요.'
        )
        return redirect('menu:billing_home', restaurant_slug=request.restaurant.slug)

    return redirect(checkout_url)


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
        # trial_ends_at / current_period_end 는 건드리지 않는다. 이미 낸 돈이나
        # 남은 체험 기간까지는 쓰는 게 맞아서 access_until 을 그대로 남긴다.
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
