"""
결제 대행사가 지켜야 할 최소 계약.

여기 없는 기능은 일부러 없는 것이다. 환불·요금제 변경·인보이스 조회 따위를
미리 추상화해 봤자 실제 대행사의 모양을 모르는 채로 만든 껍데기라 붙일 때
어차피 다 뜯게 된다. 지금 확실히 필요한 네 가지만 둔다.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping, Optional


class PaymentError(Exception):
    """
    대행사와 통신은 됐는데 결제가 성립하지 않았다.

    PaymentNotConfigured 와 구분한다. 그쪽은 '우리 설정이 없다'는 우리 잘못이고,
    이쪽은 '카드가 거절됐다' 같은 결제 자체의 실패다. 호출자가 다르게 다뤄야 한다 —
    앞은 500 으로 시끄럽게, 뒤는 사장님께 사유를 보여주고 재시도를 권한다.
    """


class PaymentNotConfigured(Exception):
    """결제 대행사가 아직 연결되지 않았는데 결제를 요구받았을 때."""


# 웹훅이 실제로 상태를 바꾸는 사건은 이 셋뿐이다.
# 대행사는 수십 종의 이벤트를 보내지만 나머지는 우리 상태 기계와 무관하다.
EVENT_PAYMENT_SUCCEEDED = 'payment_succeeded'
EVENT_PAYMENT_FAILED = 'payment_failed'
EVENT_SUBSCRIPTION_CANCELED = 'subscription_canceled'

EVENT_KINDS = (
    EVENT_PAYMENT_SUCCEEDED,
    EVENT_PAYMENT_FAILED,
    EVENT_SUBSCRIPTION_CANCELED,
)


@dataclass(frozen=True)
class BillingEvent:
    """
    대행사 웹훅을 우리 말로 옮긴 것.

    뷰는 이 모양만 안다. 회사가 바뀌어도 parse_webhook 안쪽만 바뀌고
    billing_views.webhook 은 그대로다.

    kind        : EVENT_KINDS 중 하나. 그 외 이벤트는 parse_webhook 이
                  None 을 돌려 '관심 없음'을 표시한다.
    provider_subscription_id : 어느 구독에 대한 사건인지. 이 값으로만
                  Subscription 을 찾는다. 매장 slug 를 웹훅에서 믿지 않는다.
    period_end  : 결제 성공 시 다음 결제일. 없으면 None.
    event_id    : 대행사가 준 이벤트 고유 ID. 재전송 판별용 로그 키.
                  (지금은 상태를 수렴형으로 만들어 중복을 막고 있어서
                   저장하지 않는다. apply_event 주석 참고.)
    """

    kind: str
    provider_subscription_id: str
    period_end: Optional[datetime] = None
    event_id: str = ''


class PaymentProvider:
    """
    결제 대행사 어댑터의 기반 클래스.

    새 대행사를 붙이는 사람이 채워야 할 것은 아래 다섯 가지가 전부다.
    나머지(구독 상태 기계, 권한, 화면)는 이미 돌아가고 있다.
    """

    #: settings.PAYMENT_PROVIDER 와 웹훅 URL 의 <provider> 조각에 쓰이는 이름.
    #: Subscription.provider 컬럼에도 이 값이 그대로 저장된다.
    name: str = ''

    def start_checkout(self, subscription, plan, return_url) -> str:
        """
        사장님을 대행사 결제창으로 보낼 URL 을 만든다.

        구현자가 할 일:
        - 대행사에 결제/구독 생성을 요청하고 결제 페이지 URL 을 받는다.
        - 대행사가 고객 ID·구독 ID 를 이 시점에 준다면
          subscription.provider / provider_customer_id /
          provider_subscription_id 에 채워 save() 한다. 이후 웹훅은
          provider_subscription_id 로만 매칭되므로, 여기서 안 채우면
          웹훅이 도착해도 주인을 못 찾는다.
        - 상태(status)는 건드리지 않는다. 결제 확정은 웹훅이 한다.
          여기서 미리 active 로 만들면 결제창을 닫고 나간 사장님이
          공짜로 이용하게 된다.

        return_url 은 결제 후 돌아올 우리 쪽 절대 URL 이다.
        연동 전이라면 PaymentNotConfigured 를 던진다.
        """
        raise NotImplementedError

    def cancel(self, subscription) -> None:
        """
        대행사 쪽 구독을 해지한다. 로컬 상태 변경은 호출자가 이미 했거나 할 것이다.

        구현자가 할 일: 대행사 해지 API 호출. 이미 해지된 구독에 대해
        다시 불려도 예외를 던지지 않도록 한다(사장님이 해지 버튼을 두 번
        누르는 일은 늘 일어난다).
        """
        raise NotImplementedError

    #: 이 대행사가 웹훅으로 사건을 알려주는가.
    #: 카카오페이처럼 웹훅이 없고 리다이렉트로 돌아오는 곳은 False 로 두고
    #: approve_return / charge 를 구현한다.
    pushes_webhook: bool = True

    def approve_return(self, subscription, params: Mapping[str, str]):
        """
        결제창에서 우리 쪽으로 되돌아왔을 때 최종 승인한다.

        리다이렉트형 대행사만 구현한다. params 는 복귀 URL 의 쿼리스트링이며,
        카카오페이의 경우 pg_token 이 들어 있다. 성공하면 BillingEvent 를 준다.

        구현자가 할 일:
        - 돌아온 값이 우리가 시작한 결제인지 확인한다(저장해 둔 tid 대조).
          확인 없이 승인하면 남이 만든 pg_token 으로 남의 구독을 켤 수 있다.
        - 승인 응답에서 다음 청구에 필요한 식별자(카카오페이는 SID)를 저장한다.
          이걸 놓치면 다음 달에 청구할 방법이 없다.
        """
        raise NotImplementedError

    def charge(self, subscription, raise_on_fail: bool = True):
        """
        이미 승인된 구독에 다음 회차를 청구한다.

        웹훅형 대행사는 이 메서드가 필요 없다 — 그쪽이 알아서 청구하고 결과를
        웹훅으로 알려준다. 카카오페이는 알아서 청구해 주지 않으므로 우리가
        주기를 보고 직접 건다. 그래서 이 메서드와 스케줄러가 함께 있어야 한다.
        """
        raise NotImplementedError

    def verify_webhook(self, headers: Mapping[str, str], raw_body: bytes) -> bool:
        """
        웹훅이 진짜 대행사에서 온 것인지 검증한다.

        구현자가 할 일: 대행사가 정한 서명 헤더를 raw_body 원문으로 재계산해
        상수시간 비교(hmac.compare_digest)한다. json.loads 한 결과를 다시
        직렬화해서 비교하면 공백 하나에 서명이 깨진다. 반드시 원문을 쓴다.

        확신이 없으면 False 를 돌려준다. 여기서 True 를 잘못 주면
        아무나 남의 구독을 active 로 만들 수 있다.
        """
        raise NotImplementedError

    def parse_webhook(self, raw_body: bytes) -> Optional[BillingEvent]:
        """
        검증된 원문을 BillingEvent 로 옮긴다.

        구현자가 할 일: 대행사 페이로드에서 이벤트 종류·구독 ID·다음 결제일을
        뽑아 BillingEvent 를 만든다. 우리가 관심 없는 이벤트면 None 을
        돌려준다(뷰는 200 으로 조용히 넘긴다 — 4xx 를 주면 대행사가 무한
        재시도한다).
        """
        raise NotImplementedError
