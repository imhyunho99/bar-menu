"""
도입 문의를 1년이 지나면 지운다.

개인정보 처리방침(/privacy 제3조)에 '접수일로부터 1년' 이라고 적었다. 적어
놓고 지우지 않으면 처리방침이 거짓이 된다 — 그 자체로 법 위반이다.

따로 cron 을 걸지 않고 sweep_subscriptions 끝에서 부른다. 서버의 crontab 은
배포가 건드리지 않아서, 새 줄이 필요하면 누군가 손으로 넣어야 하고 그걸
잊으면 아무 소리 없이 안 돈다. 이미 매일 도는 명령에 붙이면 배포만으로 켜진다.

Discord 로 보낸 알림은 여기서 지우지 못한다. 그 채널의 메시지는 처리방침
제6조대로 사람이 1년 안에 정리한다.
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from menu.models import ContactSubmission

RETENTION_DAYS = 365


class Command(BaseCommand):
    help = '접수일로부터 1년이 지난 도입 문의를 지운다 (개인정보 처리방침 제3조)'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='지우지 않고 몇 건인지만 본다')

    def handle(self, *args, **opts):
        cutoff = timezone.now() - timedelta(days=RETENTION_DAYS)
        old = ContactSubmission.objects.filter(created_at__lt=cutoff)
        count = old.count()
        if opts['dry_run']:
            self.stdout.write(f'1년 지난 문의 {count}건 [dry-run]')
            return
        old.delete()
        self.stdout.write(f'1년 지난 문의 {count}건 삭제')
