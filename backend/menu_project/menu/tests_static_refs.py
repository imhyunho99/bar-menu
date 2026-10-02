"""
템플릿이 가리키는 정적 파일이 실제로 있는가.

운영은 해시 매니페스트(CompressedManifestStaticFilesStorage)를 쓴다. 없는
파일을 `{% static %}` 으로 가리키면 **그 페이지가 통째로 500** 이 된다.
개발(DEBUG=True)에서는 그냥 깨진 이미지라 눈에 안 띈다.

2026-10-02 운영에서 터졌다. menu_main.html 이 'logo.png' 를 가리켰는데
실제 파일은 'site_images/logo.png' 였다. 경로 오류 자체는 그 전부터 있었고,
이번 릴리스에서 해싱이 **제대로 켜지면서** 조용한 깨진 이미지가 500 으로
바뀐 것이다(그 전에는 폐기된 STATICFILES_STORAGE 를 써서 해싱이 꺼져
있었다). 봇이 그 주소를 긁을 때마다 Sentry 와 Discord 로 알림이 왔다.
"""

import re
from pathlib import Path

from django.test import TestCase

BACKEND = Path(__file__).resolve().parent.parent
STATIC_DIR = BACKEND / 'static'
TEMPLATE_REF = re.compile(r"""\{%\s*static\s+['"]([^'"]+)['"]""")


def _collected_files():
    if not STATIC_DIR.exists():
        return set()
    return {
        str(f.relative_to(STATIC_DIR))
        for f in STATIC_DIR.rglob('*')
        if f.is_file()
    }


class EveryStaticReferenceExistsTests(TestCase):
    def test_no_template_points_at_a_missing_file(self):
        available = _collected_files()
        self.assertTrue(available, 'static 디렉터리를 못 찾았습니다')

        missing = []
        for template in BACKEND.rglob('templates/**/*.html'):
            text = template.read_text(encoding='utf-8', errors='replace')
            for line_no, line in enumerate(text.split('\n'), 1):
                for match in TEMPLATE_REF.finditer(line):
                    ref = match.group(1)
                    # {% static x %} 처럼 변수를 쓰는 것은 여기서 못 본다.
                    if '{{' in ref or '{%' in ref:
                        continue
                    if ref not in available:
                        missing.append(f'{template.relative_to(BACKEND)}:{line_no} → {ref}')

        self.assertEqual(
            missing, [],
            '없는 정적 파일을 가리킵니다. 운영에서 그 페이지가 500 이 됩니다:\n  '
            + '\n  '.join(missing),
        )
