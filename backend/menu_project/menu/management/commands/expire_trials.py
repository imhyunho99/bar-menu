"""
끝난 무료 체험을 미결제로 내리고 우리에게 알린다.

손님 화면이 닫히는 건 이 명령과 무관하다. is_usable 이 실시간으로 날짜를
보므로 체험은 정확히 만료 시각에 닫힌다. 이 명령이 하는 일은 두 가지다:
상태를 unpaid 로 내려 화면과 목록에서 '끝났다' 고 읽히게 하는 것, 그리고
사장님에게 연락할 수 있도록 우리에게 알리는 것.

charge_subscriptions 에 얹지 않았다. 그쪽은 첫 줄이 get_provider() 이고
PaymentNotConfigured 를 만나면 통째로 return 한다. 결제 대행사가 붙기 전인
지금 거기 섞으면 만료 스윕이 아예 돌지 않는다. 체험 만료는 결제와 무관하니
따로 도는 편이 맞다.

하루 한 번 cron 으로 돈다:
    0 9 * * *  python manage.py expire_trials
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from menu import notifications
from menu.models import Subscription


class Command(BaseCommand):
    help = '끝난 무료 체험을 미결제로 내리고 알림을 보낸다'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='상태를 바꾸지 않고 대상만 보여준다')

    def handle(self, *args, **opts):
        now = timezone.now()
        # 상태로 고른다. 날짜만 보면 옛 결제일을 달고 있는 파트너·해지 매장이
        # 한꺼번에 딸려 들어와 영업 중인 가게가 미결제로 떨어진다.
        lapsed = Subscription.objects.filter(
            status='trialing',
            current_period_end__lte=now,
        ).select_related('restaurant')

        self.stdout.write(f'만료된 체험 {lapsed.count()}건 (기준 {now:%Y-%m-%d %H:%M})')
        for sub in lapsed:
            label = f'{sub.restaurant.slug} · {sub.restaurant.name}'
            if opts['dry_run']:
                self.stdout.write(f'  [dry-run] {label}')
                continue

            sub.status = 'unpaid'
            sub.save(update_fields=['status', 'updated_at'])
            # 알림이 실패해도 상태는 이미 내려갔다. 그 반대였다면 웹훅이 죽은
            # 동안 체험이 영원히 이어진다.
            notifications.send_trial_expired_notification(sub)
            self.stdout.write(f'  o {label} → 미결제')
