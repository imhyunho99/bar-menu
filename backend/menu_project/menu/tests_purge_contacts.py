"""도입 문의 보관 기한. 개인정보 처리방침 제3조가 '접수일로부터 1년' 이라고 약속한다."""

from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from menu.models import ContactSubmission


class PurgeOldContactsTests(TestCase):
    def setUp(self):
        self.old = ContactSubmission.objects.create(name='오래된 문의', contact_info='010-0000-0001')
        self.fresh = ContactSubmission.objects.create(name='새 문의', contact_info='010-0000-0002')
        # created_at 은 auto_now_add 라 생성할 때 못 정한다. 만든 뒤 옮긴다.
        ContactSubmission.objects.filter(pk=self.old.pk).update(
            created_at=timezone.now() - timedelta(days=366)
        )

    def test_a_year_old_inquiry_is_deleted_and_a_new_one_stays(self):
        call_command('purge_old_contacts', stdout=StringIO())
        self.assertFalse(ContactSubmission.objects.filter(pk=self.old.pk).exists())
        self.assertTrue(ContactSubmission.objects.filter(pk=self.fresh.pk).exists())

    def test_dry_run_deletes_nothing(self):
        call_command('purge_old_contacts', dry_run=True, stdout=StringIO())
        self.assertEqual(ContactSubmission.objects.count(), 2)

    def test_the_daily_sweep_runs_it(self):
        """crontab 에 줄을 따로 넣지 않는다. 매일 도는 스윕이 불러야 실제로 지워진다."""
        call_command('sweep_subscriptions', stdout=StringIO())
        self.assertFalse(ContactSubmission.objects.filter(pk=self.old.pk).exists())
