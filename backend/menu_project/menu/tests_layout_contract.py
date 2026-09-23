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


def _widget_defaults(kind):
    """빌더 JS 안의 defaultLayout() 이 만드는 배치. kind 는 'category' | 'menu'."""
    source = _widget_css()
    start = source.index('function defaultLayout()')
    body = source[start:source.index('function mergeWithDefaults', start)]
    # isCategory 갈래가 먼저 나오고, 그 뒤가 메뉴 갈래다.
    first = body.index('return {')
    second = body.index('return {', first + 1)
    chunk = body[first:second] if kind == 'category' else body[second:]
    return [
        {
            'id': m.group('id'),
            'visible': m.group('visible') == 'true',
            'x': int(m.group('x')), 'y': int(m.group('y')),
            'w': int(m.group('w')), 'h': int(m.group('h')),
        }
        for m in re.finditer(
            r'\{id:\s*"(?P<id>[a-z_]+)",\s*name:\s*"[^"]*",\s*'
            r'visible:\s*(?P<visible>true|false),\s*'
            r'x:\s*(?P<x>\d+),\s*y:\s*(?P<y>\d+),\s*'
            r'w:\s*(?P<w>\d+),\s*h:\s*(?P<h>\d+)\}',
            chunk,
        )
    ]


class TheBuilderCanBeResetTests(TestCase):
    """
    사장님이 배치를 망쳤을 때 스스로 빠져나올 문이 있는가.

    이게 없으면 되돌리는 길이 JSON 을 직접 지우는 것뿐이고, 그건 사장님이
    할 수 있는 일이 아니다 — 나한테 연락이 와야 풀린다.
    """

    def test_the_builder_offers_a_reset_control(self):
        self.assertIn('layout-reset-btn', _widget_css())

    def test_reset_puts_the_card_back_on_the_old_render_path(self):
        """
        되돌리기가 layout_type 을 'default' 로 되돌려 놓지 않으면, 자리만
        기본값이고 손님 화면은 계속 절대배치로 그려진다. 사장님 눈에는
        '되돌렸는데 그대로' 로 보인다.
        """
        source = _widget_css()
        body = source[source.index('function defaultLayout()'):source.index('function mergeWithDefaults')]
        self.assertNotIn("layout_type: \"custom\"", body)
        self.assertEqual(body.count('layout_type: "default"'), 2)

        reset = source[source.index('const resetBtn'):]
        self.assertIn('layout = defaultLayout()', reset)
        self.assertNotIn('syncValue()', reset, 'syncValue 는 custom 으로 다시 찍는다')


class TheBuilderDefaultsMatchTheBackendTests(TestCase):
    """
    빌더 JS 의 기본 배치는 models.py 의 것을 손으로 베껴 둔 것이다. 한쪽만
    고치면 '처음 여는 사장님' 과 '되돌린 사장님' 이 서로 다른 자리를 본다.
    """

    def test_category_defaults_match(self):
        backend = [
            {k: c[k] for k in ('id', 'visible', 'x', 'y', 'w', 'h')}
            for c in default_category_layout()['components']
        ]
        self.assertEqual(_widget_defaults('category'), backend)

    def test_menu_defaults_match(self):
        backend = [
            {k: c[k] for k in ('id', 'visible', 'x', 'y', 'w', 'h')}
            for c in default_menu_layout()['components']
        ]
        self.assertEqual(_widget_defaults('menu'), backend)


class TheBuilderWorksWithAFingerTests(TestCase):
    """
    사장님은 폰이나 태블릿으로도 열어 본다.

    터치는 mousemove 를 만들지 않는다 — 탭이 끝난 뒤에야 mousedown/mouseup 이
    오고, 끄는 동안에는 아무 이벤트도 안 온다. 그래서 mouse 전용으로 짜면
    빌더가 폰에서 조용히 죽는다(캔버스는 보이는데 상자가 안 움직인다).
    2026-09-20 에 iPhone 뷰포트로 실제 터치를 보내 확인했다.
    """

    def test_dragging_listens_for_pointers_not_mice(self):
        source = _widget_css()
        for event in ('pointerdown', 'pointermove', 'pointerup'):
            self.assertIn(f"'{event}'", source)
        for event in ('mousedown', 'mousemove', 'mouseup'):
            self.assertNotIn(f"'{event}'", source)

    def test_the_browser_does_not_steal_the_drag_for_scrolling(self):
        """touch-action 이 없으면 상자 대신 페이지가 움직인다."""
        css = _widget_css()
        box_rule = css[css.index('.comp-box {'):css.index('.comp-box.selected')]
        self.assertIn('touch-action: none', box_rule)


class TheBuilderShowsEveryPieceTheCustomerScreenDrawsTests(TestCase):
    """
    빌더가 저장값을 그대로 믿으면, 조각이 나중에 늘어났을 때 그 전에
    저장한 매장에서는 새 조각이 빌더에 안 나온다.

    2026-09-23 dev 에서 실제로 그랬다 — 네 매장 전부 저장된 배치가 5조각
    (장바구니 버튼·노트 없음)이었다. 사장님은 그 둘을 볼 수도 옮길 수도
    없는데, 손님 화면 렌더러는 기본값을 돌기 때문에 기본 자리에 그렸다.
    빌더에서 본 것과 손님이 보는 것이 달랐다.
    """

    def test_the_builder_merges_saved_over_the_defaults(self):
        source = _widget_css()
        self.assertIn('function mergeWithDefaults', source)

        body = source[source.index('function mergeWithDefaults'):source.index('const parsedCount')]
        # 손님 화면 렌더러와 같은 방향이어야 한다: 기본값을 돌고 저장값을 얹는다.
        self.assertIn('defaults.components.map', body)
        self.assertNotIn('parsed.components.map(c => c)', body)

    def test_opening_the_builder_does_not_mark_a_store_as_custom(self):
        """
        여기서 custom 을 찍으면, 사장님이 설정 화면을 열어 보기만 해도
        손님 화면이 절대배치로 바뀐다.
        """
        source = _widget_css()
        body = source[source.index('function mergeWithDefaults'):source.index('const parsedCount')]
        self.assertIn("=== 'custom' ? 'custom' : 'default'", body)

    def test_the_merge_runs_before_anything_is_drawn(self):
        source = _widget_css()
        self.assertLess(
            source.index('layout = mergeWithDefaults(layout)'),
            source.index('function render()'),
            '그리기 전에 합쳐야 한다',
        )


class TheBuilderDoesNotLieAboutLegibilityTests(TestCase):
    """
    사장님이 밝은 사진 위에 흰 글자를 올려 두고도 빌더에서는 멀쩡해
    보이던 문제. 2026-09-23 실제 음식 사진으로 재 보니 메뉴명 대비가
    1.7:1 이었다 (큰 글자 기준 3:1).

    고친 방향은 셋이다 — 캔버스에 실제 사진을 깔고, 상자 배경을 없애
    사진이 비치게 하고, 글자 그림자를 손님 화면과 같게 맞췄다.
    """

    def test_the_canvas_can_carry_a_real_photo(self):
        widget = _widget_css()
        self.assertIn('sample_image_url', widget)
        self.assertIn('background-size: cover', widget)

    def test_the_boxes_do_not_act_as_a_scrim(self):
        """
        반투명 흰 배경을 깔면 그게 스크림 노릇을 해서, 안 읽히는 글자가
        읽히는 것으로 보인다. 사진을 깔아 둔 의미가 없어진다.
        """
        widget = _widget_css()
        box_rule = widget[widget.index('.comp-box {'):widget.index('.comp-box.selected')]
        self.assertIn('background: transparent', box_rule)
        self.assertNotIn('rgba(255,255,255,.12)', box_rule)

    def test_the_customer_text_carries_the_same_shadow_as_the_builder(self):
        widget = _widget_css()
        box_rule = widget[widget.index('.comp-box {'):widget.index('.comp-box.selected')]
        self.assertIn('text-shadow', box_rule, '빌더 상자에서 그림자가 사라졌습니다')

        css = (FRONTEND / 'styles' / 'globals.css').read_text(encoding='utf-8')
        layout_rule = css[css.index('.layout-text {'):css.index('}', css.index('.layout-text {'))]
        self.assertIn('text-shadow', layout_rule)
