"""
빌더가 저장하는 JSON 의 모양.

layout_type 이 'custom' 으로 안 바뀌면 렌더러가 영영 안 돈다 — 사장님은
옮기고 저장했는데 손님 화면은 그대로인, 지금과 똑같은 상태가 된다.

위젯은 바닐라 JS 라 여기서 실행할 수 없다. 소스에 그 동작이 있는지만
본다. 실제 동작은 마지막 E2E 가 본다.
"""

from pathlib import Path

from django.test import TestCase

WIDGET = (
    Path(__file__).resolve().parent
    / 'templates' / 'admin' / 'widgets' / 'layout_builder_widget.html'
)


class BuilderMarksTheLayoutCustomTests(TestCase):
    def setUp(self):
        self.source = WIDGET.read_text(encoding='utf-8')

    def test_the_widget_marks_the_layout_custom_when_it_saves(self):
        """
        syncValue 가 textarea 에 쓰는 순간이 '사장님이 손댔다' 는 뜻이다.
        """
        self.assertIn("layout.layout_type = 'custom'", self.source)

    def test_marking_happens_where_the_value_is_written(self):
        """
        표시를 다른 곳에 두면 '옮겼는데 저장은 default' 인 조합이 생긴다.
        syncValue 안에서 함께 일어나야 한다.
        """
        start = self.source.index('function syncValue()')
        end = self.source.index('}', self.source.index('textarea.value', start))
        self.assertIn("layout_type = 'custom'", self.source[start:end])


class BuilderCleansUpAfterDraggingTests(TestCase):
    """
    떼는 이벤트에 등록만 하고 정의가 없었다. ReferenceError 가 나면서
    isDragging 이 영원히 true 로 남아, 한 번 끌고 나면 마우스를 떼도
    움직일 때마다 상자가 계속 따라다녔다.
    """

    def setUp(self):
        self.source = WIDGET.read_text(encoding='utf-8')

    def test_stop_interaction_is_defined(self):
        self.assertIn('function stopInteraction()', self.source)

    def test_it_releases_the_drag_state(self):
        start = self.source.index('function stopInteraction()')
        body = self.source[start:self.source.index('function startResize', start)]
        self.assertIn('isDragging = false', body)
        self.assertIn('isResizing = false', body)

    def test_it_unhooks_the_listeners(self):
        """
        떼지 않으면 끌 때마다 같은 핸들러가 쌓여, 한 번 움직일 때 좌표가
        여러 번 계산된다.
        """
        start = self.source.index('function stopInteraction()')
        body = self.source[start:self.source.index('function startResize', start)]
        self.assertIn("removeEventListener('pointermove'", body)
        self.assertIn("removeEventListener('pointerup'", body)
        # 손가락이 화면 밖으로 나가거나 전화가 오면 pointerup 대신 이것이 온다.
        self.assertIn("removeEventListener('pointercancel'", body)


class DraggingMovesWhatIsSelectedTests(TestCase):
    """
    겹친 자리에서 엉뚱한 조각이 순간이동하던 것.

    startDrag 이 누른 상자(comp)의 좌표를 원점으로 잡고, drag() 는
    activeCompId 의 조각을 움직였다. 겹친 자리에서 selectComponentAt 이
    다른 것을 고르면 둘이 달라진다 — 그러면 고르지도 않은 조각이 누른
    상자 자리로 튄다.

    2026-09-23 dev 에서 사진을 카드 전체로 깔고 그 위 글자들을 옮기려다
    확인했다. 여섯 번 끌어서 제자리에 간 것이 하나도 없었다.
    """

    def setUp(self):
        self.source = WIDGET.read_text(encoding='utf-8')

    def _start_drag_body(self):
        start = self.source.index('function startDrag')
        return self.source[start:self.source.index('function drag(', start)]

    def test_the_drag_origin_comes_from_the_selected_piece(self):
        body = self._start_drag_body()
        self.assertIn('originalX = target.x', body)
        self.assertIn('originalY = target.y', body)
        self.assertNotIn('originalX = comp.x', body)
        self.assertNotIn('originalY = comp.y', body)

    def test_the_target_is_resolved_after_selecting(self):
        """고르기 전에 target 을 잡으면 같은 어긋남이 그대로 남는다."""
        body = self._start_drag_body()
        self.assertLess(
            body.index('selectComponentAt(e, comp)'),
            body.index('const target ='),
        )

    def test_pressing_a_stack_grabs_the_top_piece(self):
        """
        사진을 카드 전체로 깔면 사진이 늘 커서 아래에 있다. '고른 것을
        유지' 로 하면 사진이 선택된 채 붙어서, 그 위 글자를 하나도 못
        옮긴다 — 실제로 그렇게 만들어 보고 확인했다.
        """
        start = self.source.index('function selectComponentAt')
        body = self.source[start:self.source.index('function selectComponent(', start)]
        self.assertIn('ids[ids.length - 1]', body)

    def test_a_deliberate_choice_is_not_stolen_by_the_piece_on_top(self):
        """
        목록에서 고르거나 톡 눌러 아래로 내려간 것은 유지한다. 완전히
        덮인 조각을 끌 수 있는 유일한 길이다.
        """
        start = self.source.index('function selectComponentAt')
        body = self.source[start:self.source.index('function selectComponent(', start)]
        self.assertIn('activeCompId === pinnedId', body)

        # 목록 클릭과 톡 누르기 둘 다 pinnedId 를 세워야 한다.
        self.assertIn('pinnedId = comp.id', self.source)
        self.assertIn('pinnedId = pressedIds[', self.source)

    def test_a_tap_without_moving_still_reaches_the_piece_underneath(self):
        """완전히 덮인 조각에 닿는 유일한 길이다."""
        start = self.source.index('function stopInteraction')
        body = self.source[start:self.source.index('function startResize', start)]
        self.assertIn('!hasPassedThreshold', body)
        self.assertIn('pressedIds', body)
