"""
무료 티어가 화면에서 정직한가.

옛 테스트는 '랜딩이 약속한 일수 == TRIAL_DAYS' 였다. TRIAL_DAYS 를 지우면
그 테스트는 자동으로 통과해 버리고, 문구만 남아 손님이 없는 체험을
약속받는다. 그게 실제 사고라서 방향을 뒤집어 남긴다.
"""

import re
from pathlib import Path

from django.test import TestCase


class MarketingDoesNotPromiseATrialTests(TestCase):
    FRONTEND = Path(__file__).resolve().parents[3] / 'frontend' / 'src'

    # 가입 버튼이 있는 곳. 여기에 옛 문구가 남으면 손님이 속는다.
    SIGNUP_PAGES = [
        'lib/marketing-content.ts',
        'app/(marketing)/page.tsx',
        'app/(marketing)/pricing/page.tsx',
        'app/(marketing)/guide/page.tsx',
    ]

    def test_no_signup_page_promises_a_free_trial_period(self):
        for relative in self.SIGNUP_PAGES:
            with self.subTest(page=relative):
                source = (self.FRONTEND / relative).read_text(encoding='utf-8')
                promised = re.findall(r'(\d+)일(?:\s*동안)?\s*무료', source)
                self.assertEqual(
                    promised, [],
                    f'{relative} 이 아직 {promised} 일 무료 체험을 약속합니다. '
                    '체험은 폐지됐고 무료는 미리보기까지입니다.',
                )

    def test_signup_pages_say_what_is_actually_free(self):
        """
        약속을 지우기만 하면 '무료' 라는 말이 통째로 사라져 가입 유인이 없어진다.
        무엇이 무료인지는 남아 있어야 한다.
        """
        for relative in self.SIGNUP_PAGES:
            with self.subTest(page=relative):
                source = (self.FRONTEND / relative).read_text(encoding='utf-8')
                self.assertIn(
                    '미리보기', source,
                    f'{relative} 에 무료로 되는 것(미리보기) 설명이 없습니다',
                )


class TheGateIsOnByDefaultTests(TestCase):
    def test_enforcement_defaults_to_on(self):
        """
        안 켜면 menu_is_live 가 무조건 True 라 전원이 공짜다. 예전에는
        '돈 낼 방법이 없다' 가 이유였지만 이제 계좌이체가 있고, 무료로 쓸
        사람은 미리보기로 산다.
        """
        from django.conf import settings

        self.assertTrue(settings.ENFORCE_SUBSCRIPTION)


class LayoutBuilderIsAvailableTests(TestCase):
    """
    2026-09-12 에 감췄던 것을 되돌린다. 그때는 저장만 되고 손님 화면에
    닿지 않아서 조용히 거짓말을 했는데, 이제 닿는다.
    """

    def test_layout_fields_are_offered_in_admin(self):
        from django.contrib.admin.sites import site

        from menu.models import SiteSettings

        model_admin = site._registry[SiteSettings]
        shown = set()
        for _, options in model_admin.fieldsets:
            shown.update(options['fields'])

        self.assertIn('category_card_layout_json', shown)
        self.assertIn('menu_card_layout_json', shown)

    def test_the_builder_widget_is_still_wired_to_those_fields(self):
        """필드를 되살려도 위젯이 안 붙으면 JSON 원문이 그대로 보인다."""
        source = (Path(__file__).resolve().parent / 'admin.py').read_text(encoding='utf-8')
        self.assertIn('LayoutBuilderWidget', source)


class NoScreenStillMentionsTheTrialTests(TestCase):
    """
    체험을 없앤 뒤에도 문구가 여기저기 남는다. 사장님은 코드를 안 보고
    화면과 알림만 보므로, 거기 남은 '체험' 이 곧 우리가 하는 약속이 된다.
    """

    def test_the_signup_alert_does_not_announce_a_trial(self):
        from menu.models import Restaurant
        from menu.notifications import build_signup_payload

        restaurant = Restaurant.objects.create(name='새 바', slug='new-bar')
        payload = build_signup_payload(restaurant)
        embed = payload['embeds'][0]

        self.assertNotIn('체험', embed['title'])
        self.assertNotIn('체험', str(embed['fields']))

    def test_the_signup_alert_still_carries_a_way_to_reach_the_owner(self):
        """문구를 걷어내다 연락처까지 날리면 알림이 소음이 된다."""
        from django.contrib.auth.models import User

        from menu.models import Restaurant, UserProfile
        from menu.notifications import build_signup_payload

        restaurant = Restaurant.objects.create(name='새 바', slug='new-bar')
        user = User.objects.create_user('owner@example.com', password='pw-12345678')
        UserProfile.objects.create(user=user, restaurant=restaurant, phone='010-1111-2222')

        text = str(build_signup_payload(restaurant))
        self.assertIn('owner@example.com', text)
        self.assertIn('010-1111-2222', text)

    def test_no_owner_facing_template_mentions_a_trial(self):
        """
        주석은 '왜 없앴는지' 를 설명하느라 그 단어를 쓴다. 손님·사장님에게
        나가는 줄만 본다 — 한 줄씩 보면 {% comment %} 블록 안쪽을 놓친다.
        """
        import re
        from pathlib import Path

        root = Path(__file__).resolve().parent / 'templates'
        block = re.compile(r'{%\s*comment\s*%}.*?{%\s*endcomment\s*%}', re.S)
        inline = re.compile(r'{#.*?#}', re.S)

        offenders = []
        for path in list(root.glob('admin/**/*.html')) + list(root.glob('onboarding/**/*.html')):
            visible_text = inline.sub('', block.sub('', path.read_text(encoding='utf-8')))
            hits = [line.strip() for line in visible_text.splitlines() if '체험' in line]
            if hits:
                offenders.append(f'{path.name}: {hits[0][:60]}')
        self.assertEqual(offenders, [], f'화면에 체험 문구가 남았습니다: {offenders}')
