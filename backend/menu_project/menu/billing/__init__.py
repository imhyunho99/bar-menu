"""
결제 대행사 어댑터.

아직 어느 회사와 계약할지 정해지지 않았다. 그래서 이 패키지의 목적은
'대행사를 고르는 일'을 나중으로 미루되, 미룬 자리가 어디인지 코드에
명확히 남겨두는 것이다. 뷰·모델·템플릿 어디에도 특정 회사의 이름이나
페이로드 모양이 나오지 않는다.

붙일 때 손대는 곳은 세 군데뿐이다:
    1. billing/<회사>.py 에 PaymentProvider 를 구현
    2. billing/registry.py 의 PROVIDERS 에 한 줄 등록
    3. settings.PAYMENT_PROVIDER 를 그 이름으로 설정
"""

from .base import BillingEvent, PaymentNotConfigured, PaymentProvider
from .registry import get_provider, get_provider_by_name

__all__ = [
    'BillingEvent',
    'PaymentNotConfigured',
    'PaymentProvider',
    'get_provider',
    'get_provider_by_name',
]
