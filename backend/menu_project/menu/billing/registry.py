"""
어느 provider 를 쓸지 고르는 곳.

settings.py 를 건드리지 않고도 동작하도록 getattr 로 읽는다.
설정이 없으면 null — 즉 기본값은 '아무도 청구하지 않는다'이다.
"""

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .base import PaymentProvider
from .null import NullPaymentProvider

# 새 대행사를 붙일 때 여기 한 줄을 추가하는 것이 등록의 전부다.
#   'toss': TossPaymentProvider,
PROVIDERS = {
    NullPaymentProvider.name: NullPaymentProvider,
}


def get_provider_by_name(name: str) -> PaymentProvider | None:
    """
    이름으로 provider 를 찾는다. 없으면 None.

    웹훅 URL 조각처럼 바깥에서 들어온 값을 다룰 때 쓴다. 모르는 이름에
    예외를 던지면 스캐너가 던진 아무 문자열이 500 으로 잡히므로,
    호출자가 404 로 처리할 수 있게 None 을 준다.
    """
    provider_class = PROVIDERS.get(name)
    return provider_class() if provider_class else None


def get_provider() -> PaymentProvider:
    """
    settings.PAYMENT_PROVIDER 가 가리키는 provider. 설정이 없으면 null.

    이름이 등록되지 않은 값이면 예외를 던진다. 오타 하나가 조용히
    '결제 없음'으로 되돌아가면 아무도 눈치채지 못한 채 무료로 운영된다.
    """
    name = getattr(settings, 'PAYMENT_PROVIDER', '') or NullPaymentProvider.name
    provider = get_provider_by_name(name)
    if provider is None:
        raise ImproperlyConfigured(
            f"PAYMENT_PROVIDER='{name}' 는 등록되지 않은 결제 대행사입니다. "
            f"등록된 이름: {', '.join(sorted(PROVIDERS))}"
        )
    return provider
