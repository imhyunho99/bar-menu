"""
만료된 구독에 다음 회차를 청구한다.

카카오페이는 정기결제라는 이름과 달리 다음 달에 알아서 청구해 주지 않는다.
SID 를 발급해 줄 뿐이고, 실제 청구는 우리가 주기를 보고 건다. 그래서 이 명령이
돌지 않으면 모든 구독이 한 달 뒤 조용히 만료된다 — 아무 에러도 없이.

하루 한 번 cron 으로 돈다:
    0 4 * * *  python manage.py charge_subscriptions
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from menu.billing import base
from menu.billing.registry import get_provider
from menu.models import Subscription

# 청구 대상 상태. partner(무제한)와 unpaid(결제 전), canceled(해지)는 제외한다.
BILLABLE = ('active', 'past_due')


class Command(BaseCommand):
    help = '이용 기간이 끝난 구독에 다음 회차를 청구한다'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='청구하지 않고 대상만 보여준다')

    def handle(self, *args, **opts):
        provider = get_provider()
        now = timezone.now()
        due = Subscription.objects.filter(
            status__in=BILLABLE,
            current_period_end__lte=now,
        ).exclude(provider_subscription_id='').select_related('restaurant')

        self.stdout.write(f'청구 대상 {due.count()}건 (기준 {now:%Y-%m-%d %H:%M})')
        ok = failed = 0
        for sub in due:
            label = f'{sub.restaurant.slug} · {sub.get_plan_display()}'
            if opts['dry_run']:
                self.stdout.write(f'  [dry-run] {label}')
                continue
            try:
                event = provider.charge(sub, raise_on_fail=False)
            except base.PaymentNotConfigured as e:
                self.stderr.write(f'  중단: {e}')
                return
            except Exception as e:                      # noqa: BLE001
                # 한 매장의 실패가 나머지 매장의 청구를 막지 않게 한다.
                self.stderr.write(f'  ! {label} 예외 {e}')
                failed += 1
                continue

            if event.kind == base.EVENT_PAYMENT_SUCCEEDED:
                sub.status = 'active'
                if event.period_end:
                    sub.current_period_end = event.period_end
                sub.save(update_fields=['status', 'current_period_end', 'updated_at'])
                ok += 1
                self.stdout.write(f'  o {label} → {sub.current_period_end:%Y-%m-%d}')
            else:
                # 결제 실패는 past_due 로만 넘긴다. 손님 화면은 계속 열어 둔다 —
                # 카드 한 번 실패했다고 영업 중인 가게 메뉴판을 끄면 그게 더 큰 사고다.
                sub.status = 'past_due'
                sub.save(update_fields=['status', 'updated_at'])
                failed += 1
                self.stdout.write(f'  x {label} 결제 실패 → past_due')

        self.stdout.write(f'완료: 성공 {ok} / 실패 {failed}')
