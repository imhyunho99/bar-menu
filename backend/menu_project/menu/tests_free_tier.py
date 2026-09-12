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
