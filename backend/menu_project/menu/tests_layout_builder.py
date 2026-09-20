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
