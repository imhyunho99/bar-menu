"""
정적 파일 캐시 무효화.

CSS 를 고쳐 배포해도 사장님 브라우저는 옛 파일을 계속 쓴다 — 파일 이름이
그대로인데 응답에 `cache-control: max-age=2592000`(30일)이 붙기 때문이다.
2026-08-23 에 디자인을 배포하고 확인하다가 실제로 그 상태를 만났다:
서버는 새 CSS 를 주는데 브라우저는 30일짜리 캐시를 쓰고 있었다.

원인은 조용한 종류였다. settings.py 가 `STATICFILES_STORAGE` 로 해싱 저장소를
지정했는데, 그 설정은 Django 4.2 에서 폐기되고 **5.1 에서 제거**됐다.
제거된 설정은 에러를 내지 않는다. 그냥 무시되고 기본 저장소가 쓰인다 —
배포도 collectstatic 도 성공한다.

설정 파일의 글자를 본다. 런타임 값으로 확인하려 하면 로컬 .env 의 DEBUG 에
따라 결과가 달라져서, 옳고 그름이 아니라 환경을 시험하게 된다.
"""

import re
from pathlib import Path

from django.test import TestCase

SETTINGS = Path(__file__).resolve().parents[1] / 'menu_project' / 'settings.py'


class StaticStorageSettingTests(TestCase):
    def setUp(self):
        self.source = SETTINGS.read_text(encoding='utf-8')
        # 주석에는 사연을 적어 두었으므로 코드 줄만 본다
        self.code = '\n'.join(
            line for line in self.source.splitlines()
            if not line.lstrip().startswith('#')
        )

    def test_removed_setting_is_not_assigned(self):
        """
        Django 5.1 에서 제거됐다. 남겨 두면 조용히 무시되고, 다음 사람은
        '설정했는데 왜 안 먹지' 를 처음부터 다시 찾는다.
        """
        self.assertNotRegex(
            self.code, r'^\s*STATICFILES_STORAGE\s*=',
            'STATICFILES_STORAGE 는 Django 5.1 에서 제거된 설정이다. STORAGES 를 쓴다')

    def test_storages_declares_a_hashing_backend(self):
        """
        이름에 내용 해시가 붙어야 긴 캐시를 안전하게 걸 수 있다.
        해시가 없으면 캐시가 길수록 배포가 늦게 보인다.
        """
        match = re.search(r"'staticfiles'\s*:\s*\{[^}]*'BACKEND'\s*:\s*'([^']+)'",
                          self.code, re.S)
        self.assertIsNotNone(match, "STORAGES['staticfiles']['BACKEND'] 를 찾지 못했다")
        self.assertIn('Manifest', match.group(1),
                      f'{match.group(1)} 는 파일 이름에 해시를 붙이지 않는다')

    def test_storages_keeps_a_default_backend(self):
        """
        STORAGES 를 통째로 대입하면 'default' 도 같이 정의해야 한다.
        빠뜨리면 업로드(미디어)가 죽는다 — 사장님이 사진을 못 올린다.
        """
        match = re.search(r'STORAGES\s*=\s*\{(.+?)\n    \}', self.code, re.S)
        self.assertIsNotNone(match, 'STORAGES 블록을 찾지 못했다')
        self.assertIn("'default'", match.group(1),
                      "STORAGES 에 'default' 가 없다 — 파일 업로드가 죽는다")
