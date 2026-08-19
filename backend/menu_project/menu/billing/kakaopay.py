"""
카카오페이 정기결제 어댑터.

카카오페이는 웹훅을 주지 않는다. 흐름은 이렇다.

    start_checkout  → /payment/ready       결제창 URL 과 tid
    (사용자가 카카오톡에서 승인)
    approve_return  → /payment/approve     tid + pg_token → SID
    charge          → /payment/subscription  저장한 SID 로 2회차 이후 청구
    cancel          → /manage/subscription/inactive

두 가지가 다른 대행사와 다르다.
  1. 승인이 '돌아오는 길'에 일어난다. 그래서 우리가 시작한 결제가 맞는지
     저장해 둔 tid 로 대조해야 한다. 안 하면 남의 pg_token 으로 남의 구독이 켜진다.
  2. 다음 달 청구를 카카오페이가 해 주지 않는다. 우리가 주기를 보고 건다.
     그래서 charge() 와 이를 도는 관리 명령이 함께 있어야 한다.

테스트 CID 는 정기결제가 TCSUBSCRIP 다(문서 명시). 개발용 Secret key 만 있으면
계약 전에도 전 구간을 시험할 수 있다.
"""

import json
import logging
import urllib.error
import urllib.request
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .base import (
    EVENT_PAYMENT_FAILED,
    EVENT_PAYMENT_SUCCEEDED,
    BillingEvent,
    PaymentError,
    PaymentNotConfigured,
    PaymentProvider,
)
from ..models import Subscription

logger = logging.getLogger(__name__)

HOST = 'https://open-api.kakaopay.com'
TIMEOUT = 15
PERIOD_DAYS = 30


class KakaoPayProvider(PaymentProvider):
    name = 'kakaopay'
    pushes_webhook = False          # 웹훅 없음. 리다이렉트 + 우리가 거는 청구.

    # ── 설정 ──────────────────────────────────────────────────────────
    @property
    def secret_key(self):
        return getattr(settings, 'KAKAOPAY_SECRET_KEY', '') or ''

    @property
    def cid(self):
        return getattr(settings, 'KAKAOPAY_CID', '') or ''

    def _require_config(self):
        if not self.secret_key or not self.cid:
            raise PaymentNotConfigured(
                '카카오페이 키가 없습니다. KAKAOPAY_SECRET_KEY 와 KAKAOPAY_CID 를 설정하세요.'
            )

    # ── HTTP ──────────────────────────────────────────────────────────
    def _post(self, path, body):
        """
        카카오페이 REST 호출. 테스트는 이 메서드만 갈아끼운다.

        Authorization 은 'SECRET_KEY <키>' 형식이다(Bearer 가 아니다).
        """
        req = urllib.request.Request(
            f'{HOST}{path}',
            data=json.dumps(body).encode('utf-8'),
            headers={
                'Authorization': f'SECRET_KEY {self.secret_key}',
                'Content-Type': 'application/json',
            },
            method='POST',
        )
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return json.loads(r.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            detail = e.read().decode('utf-8', 'replace')[:300]
            logger.warning('kakaopay %s HTTP %s %s', path, e.code, detail)
            raise PaymentError(f'카카오페이 요청이 거절되었습니다. ({e.code})') from e
        except urllib.error.URLError as e:
            logger.warning('kakaopay %s 연결 실패 %s', path, e)
            raise PaymentError('카카오페이에 연결하지 못했습니다.') from e

    # ── 공통 ──────────────────────────────────────────────────────────
    @staticmethod
    def _amount(plan):
        return Subscription.PLAN_PRICES[plan]

    @staticmethod
    def _order_id(subscription):
        return f'barmenu-{subscription.restaurant_id}-{int(timezone.now().timestamp())}'

    @staticmethod
    def _user_id(subscription):
        """
        가맹점 회원 id. 문서상 실명·휴대폰·이메일·ID 같은 개인정보를 넣을 수 없다.
        매장 번호만 쓴다.
        """
        return f'shop-{subscription.restaurant_id}'

    @staticmethod
    def _period_end():
        return timezone.now() + timedelta(days=PERIOD_DAYS)

    # ── 1회차: 결제창 ─────────────────────────────────────────────────
    def start_checkout(self, subscription, plan, return_url) -> str:
        self._require_config()
        amount = self._amount(plan)
        body = {
            'cid': self.cid,
            'partner_order_id': self._order_id(subscription),
            'partner_user_id': self._user_id(subscription),
            'item_name': f'bar-menu {dict(Subscription.PLAN_CHOICES)[plan]} 월 구독',
            'quantity': 1,
            'total_amount': amount,
            'tax_free_amount': 0,
            'approval_url': f'{return_url}?result=approve',
            'cancel_url': f'{return_url}?result=cancel',
            'fail_url': f'{return_url}?result=fail',
        }
        data = self._post('/online/v1/payment/ready', body)
        tid = data.get('tid')
        url = data.get('next_redirect_pc_url')
        if not tid or not url:
            raise PaymentError('카카오페이가 결제창 주소를 주지 않았습니다.')

        # 상태는 건드리지 않는다. 결제창을 띄운 것과 결제된 것은 다르다.
        subscription.pending_tid = tid
        subscription.plan = plan
        subscription.save(update_fields=['pending_tid', 'plan', 'updated_at'])
        return url

    # ── 복귀: 승인 ────────────────────────────────────────────────────
    def approve_return(self, subscription, params):
        self._require_config()
        pg_token = (params or {}).get('pg_token')
        if not pg_token:
            raise PaymentError('pg_token 이 없습니다. 승인할 수 없습니다.')
        tid = subscription.pending_tid
        if not tid:
            # 우리가 시작한 결제가 아니다. 여기서 막지 않으면 남이 만든
            # pg_token 으로 남의 구독이 켜진다.
            raise PaymentError('진행 중인 결제가 없습니다.')

        data = self._post('/online/v1/payment/approve', {
            'cid': self.cid,
            'tid': tid,
            'partner_order_id': self._order_id(subscription),
            'partner_user_id': self._user_id(subscription),
            'pg_token': pg_token,
        })

        sid = data.get('sid')
        if not sid:
            # 정기결제 CID 로 승인했는데 SID 가 없으면 다음 달 청구가 불가능하다.
            # 조용히 넘어가면 한 달 뒤에야 발견된다.
            raise PaymentError('정기결제 식별자(SID)를 받지 못했습니다.')

        subscription.provider = self.name
        subscription.provider_subscription_id = sid
        subscription.pending_tid = ''      # 같은 tid 로 두 번 승인되지 않게
        subscription.save(update_fields=[
            'provider', 'provider_subscription_id', 'pending_tid', 'updated_at'])

        return BillingEvent(
            kind=EVENT_PAYMENT_SUCCEEDED,
            provider_subscription_id=sid,
            period_end=self._period_end(),
            event_id=data.get('aid') or '',
        )

    # ── 2회차 이후 ────────────────────────────────────────────────────
    def charge(self, subscription, raise_on_fail: bool = True):
        self._require_config()
        sid = subscription.provider_subscription_id
        if not sid:
            raise PaymentError('정기결제 식별자(SID)가 없어 청구할 수 없습니다.')

        try:
            data = self._post('/online/v1/payment/subscription', {
                'cid': self.cid,
                'sid': sid,
                'partner_order_id': self._order_id(subscription),
                'partner_user_id': self._user_id(subscription),
                'item_name': f'bar-menu {dict(Subscription.PLAN_CHOICES)[subscription.plan]} 월 구독',
                'quantity': 1,
                'total_amount': self._amount(subscription.plan),
                'tax_free_amount': 0,
            })
        except PaymentError:
            if raise_on_fail:
                raise
            # 카드 거절은 사고가 아니라 일상이다. 호출자(스케줄러)가 past_due 로
            # 넘길 수 있게 사건으로 돌려준다.
            return BillingEvent(kind=EVENT_PAYMENT_FAILED,
                                provider_subscription_id=sid)

        return BillingEvent(
            kind=EVENT_PAYMENT_SUCCEEDED,
            provider_subscription_id=sid,
            period_end=self._period_end(),
            event_id=data.get('aid') or '',
        )

    # ── 해지 ──────────────────────────────────────────────────────────
    def cancel(self, subscription) -> None:
        sid = subscription.provider_subscription_id
        if not sid:
            # 붙은 적 없는 구독. 사장님이 해지 버튼을 두 번 눌러도 조용해야 한다.
            return None
        self._require_config()
        try:
            self._post('/online/v1/payment/manage/subscription/inactive',
                       {'cid': self.cid, 'sid': sid})
        except PaymentError as e:
            # 이미 비활성인 SID 에도 같은 응답이 올 수 있다. 로컬 해지를
            # 대행사 사정으로 막지 않는다.
            logger.info('kakaopay 해지 응답 무시: %s', e)
        return None

    # ── 웹훅 없음 ─────────────────────────────────────────────────────
    def verify_webhook(self, headers, raw_body) -> bool:
        """카카오페이는 웹훅을 보내지 않는다. 왔다면 우리 것이 아니다."""
        return False

    def parse_webhook(self, raw_body):
        raise PaymentError('카카오페이는 웹훅을 사용하지 않습니다.')
