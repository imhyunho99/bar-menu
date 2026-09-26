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

    def test_the_photo_is_drawn_where_the_image_piece_is(self):
        """
        캔버스 배경에 통째로 깔면, 사진 조각을 줄이거나 꺼 둬도 캔버스는
        사진으로 꽉 찬다. 그러면 아래 안내문이 양쪽으로 거짓말이 된다 —
        사진 없는 자리를 사진 위로 보이게 하고, 사진을 끈 매장에도 사진을
        보여 준다. 2026-09-25 검토에서 실측으로 잡혔다.
        """
        widget = _widget_css()
        self.assertIn('sample_image_url', widget)
        # 캔버스 규칙에는 배경 사진이 없어야 한다.
        canvas_rule = widget[widget.index('.card-preview-canvas {'):widget.index('.card-preview-canvas.category-type')]
        self.assertNotIn('background-image', canvas_rule)
        self.assertNotIn('background-size', canvas_rule)
        # 상자를 그리는 쪽에서 사진 조각일 때만 깐다.
        self.assertIn("comp.id.endsWith('_image')", widget)
        self.assertIn('box.style.backgroundImage', widget)

    def test_a_hidden_image_piece_shows_no_photo(self):
        """
        숨긴 조각은 상자 자체가 안 그려진다(render 가 comp.visible 로 거른다).
        사진을 상자 안에서 그리므로, 끄면 사진도 같이 사라진다 — 손님 화면과
        같은 결과다.
        """
        widget = _widget_css()
        draw = widget[widget.index('layout.components.forEach'):widget.index('// Render in component list')]
        self.assertIn('if (comp.visible)', draw)
        self.assertLess(draw.index('if (comp.visible)'), draw.index('box.style.backgroundImage'))

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


class TheBuilderUsesTheCustomerDefaultsTests(TestCase):
    """
    사장님이 스타일을 비워 두면 손님 화면은 globals.css 의 :root 값을 쓴다.
    빌더가 그걸 모르고 전부 흰색으로 그리면, 검은 카드 위에서 거의 안 보이는
    글자(#4c4c4c 영문명, #575757 노트)가 빌더에서는 또렷하게 보인다.
    사장님은 멀쩡한 줄 알고 저장한다.

    2026-09-25 검토가 실측으로 잡았다. 값이 두 언어에 나뉘어 있으니 여기서
    대조한다 — 갈라지면 같은 거짓말이 그대로 돌아온다.
    """

    #: 빌더 상수의 키 → globals.css 의 CSS 변수 이름
    PIECES = {
        'menu_name': 'menu-name',
        'menu_name_en': 'menu-name-en',
        'menu_price': 'menu-price',
        'menu_description': 'menu-desc',
        'menu_notes': 'menu-notes',
        'category_name': 'category-name',
        'category_name_en': 'category-name-en',
    }

    def setUp(self):
        self.widget = _widget_css()
        self.css = (FRONTEND / 'styles' / 'globals.css').read_text(encoding='utf-8')

    def _builder_defaults(self):
        block = self.widget[
            self.widget.index('const CUSTOMER_TEXT_DEFAULTS'):self.widget.index('const PREVIEW_SCALE')
        ]
        return {
            m.group('id'): m.group('color').lower()
            for m in re.finditer(
                r"(?P<id>[a-z_]+):\s*\{color:\s*'(?P<color>#[0-9a-fA-F]{3,6})'", block,
            )
        }

    def _css_default(self, var_name):
        match = re.search(rf'--{var_name}-color:\s*(#[0-9a-fA-F]{{3,6}});', self.css)
        self.assertIsNotNone(match, f'globals.css 에 --{var_name}-color 가 없습니다')
        value = match.group(1).lower()
        # #fff 와 #ffffff 를 같은 것으로 본다.
        if len(value) == 4:
            value = '#' + ''.join(c * 2 for c in value[1:])
        return value

    def test_every_piece_the_builder_draws_has_a_customer_default(self):
        builder = self._builder_defaults()
        for piece in self.PIECES:
            with self.subTest(piece=piece):
                self.assertIn(piece, builder, '빌더가 이 조각의 기본색을 모릅니다')

    def test_the_colors_match_what_the_customer_sees(self):
        builder = self._builder_defaults()
        for piece, var_name in self.PIECES.items():
            with self.subTest(piece=piece):
                self.assertEqual(
                    builder[piece], self._css_default(var_name),
                    f'{piece}: 빌더와 손님 화면의 기본색이 다릅니다',
                )

    def test_an_empty_style_field_does_not_overwrite_the_default(self):
        """
        빈 칸을 '흰색'으로 읽으면 기본값을 깔아 둔 의미가 없다. 예전 코드가
        `input.value || '#ffffff'` 였다.
        """
        body = self.widget[
            self.widget.index('function updateBoxStyleFeedback'):self.widget.index('function syncValue')
        ]
        self.assertNotIn("|| '#ffffff'", body)
        self.assertIn('if (input.value) box.style.color = input.value;', body)


class TheBuilderWarnsAboutPhotolessItemsTests(TestCase):
    """
    사진 없는 메뉴가 섞여 있으면 같은 배치인데도 카드 높이가 크게 달라진다.
    2026-09-25 실측으로 같은 배치에서 156px 과 536px 이었다 — 사진 없는
    카드는 380px 가 검게 빈다.

    빌더는 사진이 **있는** 메뉴 한 장으로만 그려서, 사장님이 저장하기 전에
    그걸 알 방법이 없었다. 막지 않고 세어서 알려 준다.
    """

    def setUp(self):
        from django.contrib.auth.models import User
        from menu.models import Category, MenuItem, Restaurant, SiteSettings

        self.shop = Restaurant.objects.create(name='달빛', slug='moonlight')
        self.settings = SiteSettings.objects.create(restaurant=self.shop)
        category = Category.objects.create(restaurant=self.shop, name='안주')
        MenuItem.objects.create(
            restaurant=self.shop, category=category, name='사진 있음',
            price='1000', menu_image='menu_images/x.webp',
        )
        MenuItem.objects.create(
            restaurant=self.shop, category=category, name='사진 없음', price='2000',
        )
        self.user = User.objects.create_superuser('boss', 'b@x.test', 'pw-4471')
        self.client.force_login(self.user)

    def _html(self):
        url = f'/admin/menu/sitesettings/{self.settings.pk}/change/'
        return self.client.get(url).content.decode('utf-8')

    def test_it_counts_the_items_without_a_photo(self):
        html = self._html()
        self.assertIn('2개 중', html)
        self.assertIn('1개</strong>에 사진이 없습니다', html)

    def test_it_says_what_the_owner_can_do_about_it(self):
        """숫자만 던지면 사장님은 뭘 해야 할지 모른다."""
        html = self._html()
        self.assertIn('사진 조각을 꺼서', html)

    def test_a_store_where_everything_has_a_photo_gets_no_warning(self):
        """
        화면에는 카테고리 빌더와 메뉴 빌더가 같이 있고 각각 따로 센다.
        둘 다 채워야 경고가 사라진다 — 처음엔 카테고리 사진을 안 채워서
        이 테스트가 정직하게 실패했다.
        """
        from menu.models import Category, MenuItem
        MenuItem.objects.filter(menu_image='').update(menu_image='menu_images/y.webp')
        Category.objects.filter(category_image='').update(category_image='category_images/z.webp')
        self.assertNotIn('사진이 없습니다', self._html())

    def test_the_category_builder_counts_categories_not_menus(self):
        """둘이 같은 숫자를 쓰면 사장님이 엉뚱한 것을 채우러 간다."""
        html = self._html()
        self.assertIn('1개 중', html)   # 카테고리 1개 (사진 없음 1)
        self.assertIn('2개 중', html)   # 메뉴 2개 (사진 없음 1)
