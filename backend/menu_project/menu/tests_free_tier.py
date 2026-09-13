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


class LayoutBuilderIsHiddenTests(TestCase):
    def test_layout_json_fields_are_not_offered_in_admin(self):
        """
        빌더는 저장까지만 되고 손님 화면에 닿지 않는다(별도 스펙에서 고친다).
        그동안 열어 두면 무료 티어의 핵심 화면이 조용히 거짓말을 한다 —
        사장님이 배치를 옮기고 저장해도 아무 일도 일어나지 않는다.
        """
        from django.contrib.admin.sites import site

        from menu.models import SiteSettings

        model_admin = site._registry[SiteSettings]
        shown = set()
        for _, options in model_admin.fieldsets:
            shown.update(options['fields'])

        self.assertNotIn('category_card_layout_json', shown)
        self.assertNotIn('menu_card_layout_json', shown)
