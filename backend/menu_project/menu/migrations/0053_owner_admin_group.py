"""
사장님이 Django admin 의 디자인 기능을 쓸 수 있게 권한 그룹을 만든다.

메뉴판 레이아웃 빌더와 디자인 설정은 Django admin 에만 있는데, 셀프가입은
is_staff 만 주고 모델 권한을 하나도 주지 않았다. 그래서 사장님이 /admin/ 에
들어가면 빈 화면을 봤다 — 기능을 만들어 놓고 문을 안 연 상태였다.

권한을 계정에 직접 붙이지 않고 그룹으로 준다. 나중에 권한을 조정할 때 이미
가입한 사장님들을 일일이 찾아다니지 않아도 되기 때문이다.

주지 않는 것이 중요하다. 권한은 늘리기는 쉽고 줄이기는 어렵다 — 이미 받은
사람에게서 뺏는 일이 되기 때문이다.

  Restaurant         RestaurantAdmin.has_module_permission 이 이미 막지만,
                     권한 자체를 안 주는 편이 이중으로 안전하다
  ContactSubmission  남의 매장 문의다
  User               계정 관리는 우리 일이다
  SiteSettings 삭제  지우면 그 매장 손님 화면이 통째로 깨진다. 고칠 수는
                     있어도 지울 수는 없다
"""

from django.db import migrations

OWNER_GROUP_NAME = '매장 사장님'

# (모델, 줄 권한) — codename 은 Django 가 만드는 add_/change_/delete_/view_ 규약을 따른다.
OWNER_PERMISSIONS = [
    # 디자인·레이아웃. 레이아웃 빌더 위젯이 이 화면에 붙어 있다.
    ('sitesettings', ['view', 'change']),
    # 매장이 생길 때 post_save 가 하나 만들어 주므로 add 도 열어 둔다 —
    # 어드민에서 손으로 만든 옛 매장에 설정이 없는 경우가 있다.
    ('sitesettings', ['add']),
    ('category', ['view', 'add', 'change', 'delete']),
    ('menuitem', ['view', 'add', 'change', 'delete']),
    # MenuItem 화면의 인라인. 부모만 열어 두면 인라인이 읽기 전용이 된다.
    ('menuitempairing', ['view', 'add', 'change', 'delete']),
]


def _ensure_permissions_exist(apps):
    """
    Permission 행을 미리 만든다.

    Django 는 Permission 을 post_migrate 신호에서 만든다 — 즉 **모든
    마이그레이션이 끝난 뒤**다. 그래서 마이그레이션 도중에 조회하면 아무것도
    없고, 그룹이 권한 0개로 만들어진 채 배포가 초록불로 끝난다. 사장님은
    여전히 빈 화면을 보는데 아무 에러도 없다 — 조용히 실패하는 종류다.
    """
    from django.apps import apps as global_apps
    from django.contrib.auth.management import create_permissions

    # 마이그레이션이 넘겨주는 apps 는 과거 상태의 스텁이라 models_module 이 없다.
    # create_permissions 는 실제 앱 설정을 요구하므로 전역 레지스트리를 쓴다.
    app_config = global_apps.get_app_config('menu')
    create_permissions(app_config, verbosity=0)


def _owner_group(apps):
    """그룹을 만들고 권한을 맞춘다. 여러 번 돌려도 결과가 같다."""
    _ensure_permissions_exist(apps)
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')

    group, _ = Group.objects.get_or_create(name=OWNER_GROUP_NAME)

    wanted = []
    for model, actions in OWNER_PERMISSIONS:
        for action in actions:
            perm = Permission.objects.filter(
                codename=f'{action}_{model}', content_type__app_label='menu'
            ).first()
            if perm is None:
                # 여기 오면 안 된다. _ensure_permissions_exist 가 실패했거나
                # 모델 이름이 바뀐 것이다. 조용히 넘기면 사장님이 빈 화면을 보고,
                # 우리는 아무 에러도 못 본다.
                raise LookupError(
                    f'menu.{action}_{model} 권한을 찾지 못했습니다. '
                    'OWNER_PERMISSIONS 의 모델 이름을 확인하세요.'
                )
            wanted.append(perm)

    group.permissions.set(wanted)
    return group


def grant_owner_group(apps, schema_editor):
    """
    그룹을 만들고, 이미 가입한 사장님들을 넣는다.

    마이그레이션 전에 들어온 계정은 그룹이 없어서 여전히 빈 화면을 본다.
    실제로 dev 의 tech 매장이 그 상태였다.
    """
    from django.apps import apps as global_apps

    apps = apps or global_apps
    User = apps.get_model('auth', 'User')
    UserProfile = apps.get_model('menu', 'UserProfile')

    group = _owner_group(apps)

    owner_ids = UserProfile.objects.exclude(restaurant__isnull=True).values_list('user_id', flat=True)
    # 슈퍼유저는 넣지 않는다. 이미 전부 볼 수 있고, 넣으면 권한 출처가 둘이
    # 되어 나중에 그룹을 손볼 때 무엇이 바뀌는지 알기 어려워진다.
    for user in User.objects.filter(pk__in=list(owner_ids), is_superuser=False):
        user.groups.add(group)


def revoke_owner_group(apps, schema_editor):
    """
    되돌릴 때 그룹만 지운다. 계정의 is_staff 는 건드리지 않는다 —
    그건 이 마이그레이션이 준 게 아니다.
    """
    from django.apps import apps as global_apps

    apps = apps or global_apps
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name=OWNER_GROUP_NAME).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('menu', '0052_image_dimensions_for_cls'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunPython(grant_owner_group, revoke_owner_group),
    ]
