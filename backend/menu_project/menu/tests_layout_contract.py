"""
빌더와 렌더러가 같은 값을 보고 있는가.

빌더 캔버스가 320×240 인데 손님 카드가 4:5 로 그려지면, 사장님이 맞춰
놓은 배치가 손님 화면에서 어긋난다. 그 어긋남은 화면에 아무 표시도
남기지 않는다 — 사장님만 '내가 놓은 대로가 아니네' 하고 만다.

값이 두 곳(Django 템플릿의 CSS, 프론트의 상수)에 나뉘어 있어 여기서 대조한다.

여기는 **두 언어에 걸친 것만** 본다. 렌더러가 규칙을 실제로 지키는지는
frontend 의 vitest 가 진짜로 렌더해서 확인한다(`npm test`). 예전에는 그것도
여기서 소스를 문자열로 뒤져서 봤는데, 함수 이름만 바꿔도 통과하는 방식이라
테스트가 초록불인 채로 기능이 죽을 수 있었다.
"""

import re
from pathlib import Path

from django.test import TestCase

from menu.models import default_category_layout, default_menu_layout

FRONTEND = Path(__file__).resolve().parents[3] / 'frontend' / 'src'
WIDGET = (
    Path(__file__).resolve().parent
    / 'templates' / 'admin' / 'widgets' / 'layout_builder_widget.html'
)


def _widget_css():
    return WIDGET.read_text(encoding='utf-8')


def _canvas_height(kind):
    """빌더 캔버스 높이(px). .card-preview-canvas.<kind>-type 의 height."""
    match = re.search(
        r'\.card-preview-canvas\.' + kind + r'-type\s*\{[^}]*height:\s*(\d+)px',
        _widget_css(), re.S,
    )
    assert match, f'{kind}-type 캔버스 높이를 위젯에서 못 찾았습니다'
    return int(match.group(1))


def _canvas_width():
    match = re.search(
        r'\.card-preview-canvas\s*\{[^}]*width:\s*(\d+)px', _widget_css(), re.S,
    )
    assert match, '캔버스 너비를 위젯에서 못 찾았습니다'
    return int(match.group(1))


class AspectRatiosMatchTheBuilderTests(TestCase):
    def _front_aspect(self, kind):
        source = (FRONTEND / 'lib' / 'layout.ts').read_text(encoding='utf-8')
        match = re.search(kind + r":\s*'(\d+)\s*/\s*(\d+)'", source)
        self.assertTrue(match, f'layout.ts 에 {kind} 비율이 없습니다')
        return int(match.group(1)), int(match.group(2))

    def test_category_card_matches_the_category_canvas(self):
        w, h = self._front_aspect('category')
        self.assertAlmostEqual(w / h, _canvas_width() / _canvas_height('category'), places=3)

    def test_menu_card_matches_the_menu_canvas(self):
        w, h = self._front_aspect('menu')
        self.assertAlmostEqual(w / h, _canvas_width() / _canvas_height('menu'), places=3)


class ComponentIdsMatchTheDefaultsTests(TestCase):
    """
    렌더러가 모르는 id 가 기본값에 있으면 그 조각은 영영 안 그려진다.
    반대로 렌더러에만 있는 id 는 아무 데이터도 못 받는다.
    """

    def _front_ids(self, name):
        source = (FRONTEND / 'lib' / 'layout.ts').read_text(encoding='utf-8')
        block = re.search(name + r'\s*=\s*\[(.*?)\]', source, re.S)
        self.assertTrue(block, f'layout.ts 에 {name} 가 없습니다')
        return set(re.findall(r"'([a-z_]+)'", block.group(1)))

    def test_category_ids_match(self):
        backend = {c['id'] for c in default_category_layout()['components']}
        self.assertEqual(self._front_ids('CATEGORY_COMPONENT_IDS'), backend)

    def test_menu_ids_match(self):
        backend = {c['id'] for c in default_menu_layout()['components']}
        self.assertEqual(self._front_ids('MENU_COMPONENT_IDS'), backend)


class MenuLayoutCoversWhatTheCardDrawsTests(TestCase):
    """
    custom 이면 display_mode 를 무시하고 빌더가 배치를 전부 정한다.
    빌더가 모르는 조각이 있으면 켜는 순간 그게 사라진다.
    """

    def test_the_cart_button_is_a_component(self):
        ids = {c['id'] for c in default_menu_layout()['components']}
        self.assertIn('cart_button', ids)

    def test_notes_are_a_component(self):
        ids = {c['id'] for c in default_menu_layout()['components']}
        self.assertIn('menu_notes', ids)

    def test_every_component_has_a_place(self):
        for component in default_menu_layout()['components']:
            with self.subTest(component=component['id']):
                self.assertLessEqual(component['x'] + component['w'], 100, '카드 밖으로 나갑니다')
                self.assertLessEqual(component['y'] + component['h'], 100, '카드 밖으로 나갑니다')
