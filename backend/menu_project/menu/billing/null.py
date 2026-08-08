"""
대행사가 정해지기 전까지 쓰는 기본 provider.

이 provider 의 유일한 임무는 '아무에게도 돈을 청구하지 않는다'는 사실을
숨기지 않는 것이다.
"""

from typing import Mapping, Optional

from .base import BillingEvent, PaymentNotConfigured, PaymentProvider


class NullPaymentProvider(PaymentProvider):
    name = 'null'

    def start_checkout(self, subscription, plan, return_url) -> str:
        """
        결제창 URL 대신 예외를 던진다.

        센티널(빈 문자열이나 None)을 돌려주는 쪽도 생각했지만 예외로 정했다.
        센티널은 호출자가 검사를 잊는 순간 조용히 통과한다 — redirect(None)
        이 되거나, 더 나쁘게는 '결제 완료' 화면으로 넘어간다. 돈 문제에서
        가장 위험한 실패는 크래시가 아니라 '성공한 척'이다. 예외는 잊을 수
        없다: 뷰가 명시적으로 잡아서 '결제 연동 전' 화면을 그리거나,
        안 잡으면 500 으로 시끄럽게 터진다. 둘 다 가짜 성공보다 낫다.
        """
        raise PaymentNotConfigured(
            "결제 대행사가 연결되지 않았습니다. settings.PAYMENT_PROVIDER 를 확인하세요."
        )

    def cancel(self, subscription) -> None:
        """대행사가 없으니 알릴 곳도 없다. 로컬 해지는 호출자가 이미 처리한다."""
        return None

    def verify_webhook(self, headers: Mapping[str, str], raw_body: bytes) -> bool:
        """
        항상 False.

        연결된 대행사가 없는데 웹훅이 왔다면 그건 정상 트래픽이 아니다.
        """
        return False

    def parse_webhook(self, raw_body: bytes) -> Optional[BillingEvent]:
        # verify_webhook 이 항상 False 라 뷰는 여기까지 오지 않는다.
        # 누군가 검증을 건너뛰고 직접 부르는 경우를 대비해 막아둔다.
        raise PaymentNotConfigured("결제 대행사가 연결되지 않았습니다.")
