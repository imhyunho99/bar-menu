"""
화면과 알림에 장식용 이모지가 없는가.

이모지를 섹션 마커나 버튼 아이콘으로 쓰면 화면이 만들다 만 것처럼 읽힌다.
기기마다 다르게 그려지고, 매장이 고른 색과도 따로 논다.

상태를 나타내는 글자(✓, ⋮⋮)는 장식이 아니라 정보라 남긴다 — 완료 표시,
드래그 핸들, 요금표의 포함 여부 같은 것들이다.
"""

import re
from pathlib import Path

from django.test import TestCase

MENU = Path(__file__).resolve().parent
FRONTEND = MENU.parents[2] / 'frontend' / 'src'

# 그림 이모지. 기호(✓ ⋮ · ▶)는 여기 안 걸린다.
PICTOGRAPH = re.compile('[\U0001F300-\U0001FAFF\U0001F000-\U0001F2FF]')


def _offenders(paths):
    found = []
    for path in paths:
        if any(part in str(path) for part in ('__pycache__', 'migrations', 'node_modules')):
            continue
        if path.name.startswith('tests_'):
            continue
        try:
            text = path.read_text(encoding='utf-8')
        except (UnicodeDecodeError, OSError):
            continue
        for number, line in enumerate(text.splitlines(), 1):
            if PICTOGRAPH.search(line):
                found.append(f'{path.name}:{number} {line.strip()[:60]}')
    return found


class NoDecorativeEmojiTests(TestCase):
    def test_discord_alerts_carry_no_pictographs(self):
        """
        알림은 우리가 읽는 것이지만, 제목에 이모지가 붙으면 목록이
        장난스러워져 진짜 급한 것을 못 고른다.
        """
        self.assertEqual(_offenders([MENU / 'notifications.py']), [])

    def test_owner_screens_carry_no_pictographs(self):
        self.assertEqual(_offenders((MENU / 'templates' / 'admin').rglob('*.html')), [])

    def test_customer_and_marketing_screens_carry_no_pictographs(self):
        paths = list((MENU / 'templates' / 'menu').rglob('*.html'))
        paths += list((MENU / 'templates' / 'onboarding').rglob('*.html'))
        paths += list((FRONTEND / 'components').rglob('*.tsx'))
        paths += list((FRONTEND / 'app').rglob('*.tsx'))
        self.assertEqual(_offenders(paths), [])

    def test_status_marks_are_left_alone(self):
        """
        ✓ 는 장식이 아니라 상태다. 이 테스트가 그것까지 지우게 만들면 안 된다.
        """
        toast = (MENU / 'templates' / 'admin' / 'dashboard.html').read_text(encoding='utf-8')
        self.assertIn('✓', toast)
