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
