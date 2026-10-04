"""
저장 버튼을 두 번 눌러 같은 걸 두 개 만드는 사고를 막았는가.

2026-09-30 새벽 bid 사장님이 카테고리 "PNN" 을 3개, 메뉴 "MENU" 를 2개
만들었다가 손으로 지웠다. 같은 초의 uwsgi 로그에 write error(Broken pipe)가
있었다 — 저장은 커밋됐는데 응답이 브라우저에 닿지 못했고, 화면이 그대로니
또 누른 것이다. /admin/menu/category/add/?_popup=1 에 nginx 499 가 8건.

여기서 보는 것은 셋이다.

1. 가드 스크립트가 **POST 폼이 있는 모든 살아 있는 화면**에 붙어 있는가.
   이 레포는 "한쪽만 고치는" 실수를 두 번 했다(QR 주소, 정적 경로). 그래서
   파일을 훑어서 센다.
2. Django admin 의 실제 변경 폼에 렌더되는가. 팝업까지 본다 — 팝업이 바로
   사고가 난 화면이다.
3. 가드가 submit 버튼을 disabled 로 만들지 않는가. **이게 제일 중요하다.**
   제출 핸들러에서 버튼을 disabled 로 만들면 브라우저가 그 버튼을 폼
   데이터에서 뺀다. Django admin 은 `_save`/`_continue`/`_addanother` 라는
   버튼 **이름**이 POST 에 왔는지로 다음 화면을 정하므로, 그 순간 "저장하고
   계속 편집" 이 조용히 "저장" 으로 바뀐다. 저장은 되고 이동만 틀려서
   한참 못 알아챈다.
"""

import re
from pathlib import Path

from django.contrib.auth.models import Permission, User
from django.test import TestCase

from menu.models import Category, Restaurant, UserProfile

BACKEND = Path(__file__).resolve().parent.parent
GUARD_JS = BACKEND / 'static' / 'js' / 'admin_submit_guard.js'
TEMPLATES = BACKEND / 'menu' / 'templates'

# 사장님이 실제로 쓰는, POST 폼이 있는 화면들. 뷰에서 render 되는 것만 넣는다
# (add_category.html, menu_import_preview.html 은 라우팅이 없다).
POST_FORM_TEMPLATES = [
    'admin/base_site.html',      # Django admin 전체 + ?_popup=1
    'admin/category_form.html',
    'admin/menu_form.html',
    'admin/billing.html',        # 중복 제출 = 결제 요청이 두 건 생긴다
    'admin/menu_import.html',
    'admin/login.html',
]

COMMENT = re.compile(r'(^\s*//.*$)|(/\*.*?\*/)', re.MULTILINE | re.DOTALL)


def _code_only(text):
    """주석을 지운 소스. 예전에 내가 적어 둔 설명문이 검사에 걸려 통과한 적이 있다."""
    return COMMENT.sub('', text)


class TheGuardIsWiredIntoEveryPostFormTests(TestCase):
    def test_the_script_file_exists(self):
        self.assertTrue(GUARD_JS.exists(), f'{GUARD_JS} 가 없습니다')

    def test_every_live_post_form_template_loads_it(self):
        missing = []
        for name in POST_FORM_TEMPLATES:
            path = TEMPLATES / name
            self.assertTrue(path.exists(), f'{name} 이 없습니다 — 목록을 고쳐야 합니다')
            if 'admin_submit_guard.js' not in path.read_text(encoding='utf-8'):
                missing.append(name)

        self.assertEqual(
            missing, [],
            '이 화면들은 아직 저장 버튼을 두 번 누를 수 있습니다:\n  '
            + '\n  '.join(missing),
        )


class TheGuardDoesNotEatThePressedButtonTests(TestCase):
    """
    가드가 눌린 버튼의 name 을 POST 에서 빼앗으면 안 된다.
    """

    def setUp(self):
        self.source = _code_only(GUARD_JS.read_text(encoding='utf-8'))

    def test_it_never_disables_a_submit_button(self):
        self.assertNotIn(
            'disabled', self.source,
            'disabled 를 쓰면 눌린 버튼이 POST 에서 사라집니다. '
            '"저장하고 계속 편집" 이 조용히 "저장" 으로 바뀝니다.',
        )

    def test_it_never_rewrites_a_button_name_or_value(self):
        for forbidden in ('.name =', '.value =', 'setAttribute(\'name\'', 'removeAttribute'):
            self.assertNotIn(
                forbidden, self.source,
                f'{forbidden} — 버튼의 이름/값을 건드리면 Django 가 다음 화면을 못 정합니다',
            )

    def test_it_leaves_get_forms_alone(self):
        """검색·필터 폼까지 잠그면 검색어를 고쳐 다시 누르는 게 안 된다."""
        self.assertIn('form[method="post"]', self.source)
        self.assertNotIn('querySelectorAll(\'form\')', self.source)

    def test_it_bails_when_another_handler_already_cancelled(self):
        """
        billing.html 의 해지 폼은 `onsubmit="return confirm(...)"` 이다.
        "취소" 를 누르면 제출이 막힌 채로 가드까지 온다. 그걸 저장으로 세면
        아무것도 안 보낸 폼이 잠긴 채로 남는다.
        """
        self.assertIn('defaultPrevented', self.source)

    def test_it_eventually_releases(self):
        """응답이 영영 안 오는 경우 영구히 잠기면 중복보다 나쁘다."""
        self.assertIn('setTimeout', self.source)


class TheGuardReachesTheRealAdminPageTests(TestCase):
    def setUp(self):
        self.restaurant = Restaurant.objects.create(name='가드 시험', slug='guard-test')
        Category.objects.create(restaurant=self.restaurant, name='안주')

        self.owner = User.objects.create_user(
            'guard@example.com', password='pw-55213', is_staff=True,
        )
        UserProfile.objects.create(user=self.owner, restaurant=self.restaurant)
        for code in ('add_category', 'change_category', 'view_category'):
            perm = Permission.objects.filter(codename=code).first()
            if perm:
                self.owner.user_permissions.add(perm)
        self.client.force_login(self.owner)

    def test_the_change_form_serves_it(self):
        response = self.client.get('/admin/menu/category/add/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'admin_submit_guard.js')

    def test_the_popup_serves_it_too(self):
        """사고가 난 화면이 정확히 여기다."""
        response = self.client.get('/admin/menu/category/add/?_popup=1')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'admin_submit_guard.js')

    def test_the_save_buttons_are_still_named_the_way_django_expects(self):
        """
        가드가 버튼을 건드리지 않는다는 것을 렌더된 HTML 에서도 확인한다.
        소스 검사만으로는 템플릿이 버튼을 바꿔치기한 경우를 못 본다.
        """
        response = self.client.get('/admin/menu/category/add/')
        html = response.content.decode()
        for name in ('_save', '_addanother', '_continue'):
            self.assertIn(f'name="{name}"', html, f'{name} 버튼이 사라졌습니다')
