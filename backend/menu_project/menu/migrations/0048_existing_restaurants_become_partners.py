"""
셀프가입 이전부터 있던 매장을 무제한 파트너로 못박는다.

구독 게이트가 'ENFORCE_SUBSCRIPTION 이 켜지면 구독 없는 매장은 잠근다' 로
바뀌었다. 그 전까지 손으로 만들어 쓰던 매장들은 구독 레코드가 없거나
체험 상태로만 남아 있어서, 이 마이그레이션이 없으면 게이트를 켜는 순간
영업 중인 가게의 메뉴판이 한꺼번에 꺼진다.

active/past_due/canceled 는 건드리지 않는다. 결제나 해지로 이미 뜻이 정해진
상태라 파트너로 덮으면 해지한 매장이 되살아난다.
"""

from django.db import migrations

PARTNER = 'partner'
LEGACY_TRIAL = 'trialing'


def make_existing_restaurants_partners(apps, schema_editor):
    Restaurant = apps.get_model('menu', 'Restaurant')
    Subscription = apps.get_model('menu', 'Subscription')

    Subscription.objects.filter(status=LEGACY_TRIAL).update(status=PARTNER)

    covered = set(Subscription.objects.values_list('restaurant_id', flat=True))
    Subscription.objects.bulk_create([
        Subscription(restaurant_id=pk, status=PARTNER)
        for pk in Restaurant.objects.exclude(pk__in=covered).values_list('pk', flat=True)
    ])


def unmake_partners(apps, schema_editor):
    """
    되돌릴 때 파트너를 체험으로 되돌리지 않는다.

    체험 종료일을 지어낼 방법이 없어서, 되돌리는 순간 만료 판정에 걸려
    가게가 꺼진다. 상태를 그대로 두는 편이 안전하다. status 의 choices 는
    DB 제약이 아니라서 옛 코드에서도 값 자체는 문제를 일으키지 않는다.
    """


class Migration(migrations.Migration):

    dependencies = [
        ('menu', '0047_remove_subscription_trial_ends_at_and_more'),
    ]

    operations = [
        migrations.RunPython(make_existing_restaurants_partners, unmake_partners),
    ]
