"""
멀티테넌시 위생.

이 서비스는 원래 단일 매장('Bidbar')용으로 만들어졌다가 여러 매장을 받는
SaaS 가 됐다. 그 시절 상호가 템플릿에 남아 있으면, 가입한 사장님이 자기
관리 화면에서 남의 가게 이름을 보게 된다. 심사자도 그걸 본다.
"""

from pathlib import Path

from django.test import TestCase

TEMPLATE_ROOT = Path(__file__).resolve().parent / 'templates'

# 매장 하나를 가리키던 옛 상호. 어떤 대소문자로도 템플릿에 남으면 안 된다.
LEGACY_BRAND = 'bidbar'


class NoHardcodedLegacyBrandTests(TestCase):
    def test_no_template_hardcodes_the_legacy_store_name(self):
        offenders = []
        for path in sorted(TEMPLATE_ROOT.rglob('*.html')):
            for lineno, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
                if LEGACY_BRAND in line.lower():
                    offenders.append(f'{path.relative_to(TEMPLATE_ROOT)}:{lineno}: {line.strip()}')

        self.assertEqual(
            offenders, [],
            '옛 매장 상호가 템플릿에 남아 있습니다. 매장명은 request.restaurant 에서 오고, '
            '없을 때의 대체값은 서비스명이어야 합니다:\n' + '\n'.join(offenders),
        )
