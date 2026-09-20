"""
빌더와 렌더러가 같은 값을 보고 있는가.

빌더 캔버스가 320×240 인데 손님 카드가 4:5 로 그려지면, 사장님이 맞춰
놓은 배치가 손님 화면에서 어긋난다. 그 어긋남은 화면에 아무 표시도
남기지 않는다 — 사장님만 '내가 놓은 대로가 아니네' 하고 만다.

값이 두 곳(Django 템플릿의 CSS, 프론트의 상수)에 나뉘어 있어 여기서 대조한다.
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


class CategoryCardHonorsTheLayoutTests(TestCase):
    """
    프론트에 JS 테스트 러너가 없다. 렌더러가 규칙을 실제로 쓰는지 소스로
    확인하고, 그려진 결과는 마지막 E2E 가 본다.
    """

    def setUp(self):
        self.source = (FRONTEND / 'components' / 'CategoryCard.tsx').read_text(encoding='utf-8')

    def test_it_branches_on_the_layout_type(self):
        self.assertIn('isCustomLayout', self.source)

    def test_it_fills_missing_components_from_the_defaults(self):
        self.assertIn('resolveComponents', self.source)

    def test_it_uses_the_shared_aspect_ratio(self):
        self.assertIn('CARD_ASPECT', self.source)

    def test_it_keeps_the_class_names_that_carry_the_owner_fonts(self):
        """
        폰트·색·크기는 styles.ts 가 이 클래스들에 CSS 변수로 주입한다.
        클래스를 갈면 사장님이 맞춰 둔 글꼴이 통째로 날아간다.
        """
        for klass in ('category-name-ko', 'category-name-en'):
            self.assertIn(klass, self.source)

    def test_it_draws_the_category_image(self):
        """기본 카드에는 이미지 자리가 아예 없었다. 배치에는 있다."""
        self.assertIn('category_image', self.source)


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
