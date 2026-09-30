"""
이용 기간을 훑어 끝난 것을 내리고, 곧 끝날 것을 알린다.

손님 화면이 닫히는 건 이 명령과 무관하다. is_usable 이 실시간으로 날짜를
보므로 기간은 정확히 만료 시각에 닫힌다. 이 명령이 하는 일은 두 가지다:
상태를 unpaid 로 내려 화면과 목록에서 '끝났다' 고 읽히게 하는 것, 그리고
연장을 안내할 수 있도록 우리에게 알리는 것.

charge_subscriptions 에 얹지 않았다. 그쪽은 첫 줄이 get_provider() 이고
PaymentNotConfigured 를 만나면 통째로 return 한다. 결제 대행사가 없는 지금
거기 섞으면 스윕이 아예 돌지 않는다.

하루 한 번 cron 으로 돈다:
    0 9 * * *  python manage.py sweep_subscriptions
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from menu import notifications
from menu.models import Subscription

# 며칠 전에 알릴지. 입금하고 우리가 통장을 확인하는 데 걸리는 시간을 감안한다.
WARN_DAYS = 7


class Command(BaseCommand):
    help = '끝난 이용 기간을 미결제로 내리고, 곧 끝날 매장을 알린다'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='상태를 바꾸지 않고 대상만 보여준다')

    def handle(self, *args, **opts):
        now = timezone.now()
        dry_run = opts['dry_run']

        # 상태로 먼저 거른다. 날짜만 보면 옛 결제일을 달고 있는 파트너·해지
        # 매장이 딸려 들어와 영업 중인 가게가 미결제로 떨어진다.
        #
        # 날짜가 없는 구독(= 한 번도 연 적 없는 무료 매장)도 여기서 빠진다.
        # 그건 만료가 아니라 아직 시작하지 않은 것이다 — 섞이면 가입만 하고
        # 둘러보는 사장님마다 '끝났습니다' 알림이 간다.
        lapsed = Subscription.objects.filter(
            status='active',
            current_period_end__lte=now,
        ).select_related('restaurant')

        self.stdout.write(f'만료 {lapsed.count()}건 (기준 {now:%Y-%m-%d %H:%M})')
        for subscription in lapsed:
            label = f'{subscription.restaurant.slug} · {subscription.restaurant.name}'
            if dry_run:
                self.stdout.write(f'  [dry-run] {label}')
                continue
            subscription.status = 'unpaid'
            subscription.save(update_fields=['status', 'updated_at'])
            # 알림이 실패해도 상태는 이미 내려갔다. 반대였다면 웹훅이 죽은
            # 동안 기간이 영원히 이어진다.
            notifications.send_subscription_expired_notification(subscription)
            self.stdout.write(f'  o {label} → 미결제')

        soon = Subscription.objects.filter(
            status='active',
            current_period_end__gt=now,
            current_period_end__lte=now + timedelta(days=WARN_DAYS),
        ).select_related('restaurant')

        self.stdout.write(f'곧 만료 {soon.count()}건')
        for subscription in soon:
            label = f'{subscription.restaurant.slug} · {subscription.restaurant.name}'
            days_left = max(0, (subscription.current_period_end - now).days)
            if dry_run:
                self.stdout.write(f'  [dry-run] {label} ({days_left}일)')
                continue
            notifications.send_expiring_soon_notification(subscription, days_left)
            self.stdout.write(f'  o {label} ({days_left}일 남음)')
