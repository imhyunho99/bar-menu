"""
미리보기 토큰.

사장님이 결제 전에 자기 메뉴판을 실제 화면으로 보는 통로다. 링크 하나로
열리므로, 그 링크가 곧 결제 우회로가 되지 않도록 수명과 대상이 서명에
박혀 있어야 한다.
"""

from django.test import TestCase

from menu.preview import (
    PREVIEW_MAX_AGE_SECONDS,
    check_preview_token,
    make_preview_token,
)


class PreviewTokenTests(TestCase):
    def test_a_fresh_token_opens_its_own_store(self):
        token = make_preview_token('bid')
        self.assertTrue(check_preview_token('bid', token))

    def test_a_token_does_not_open_another_store(self):
        """서명에 slug 가 들어간다. 한 장 받아서 남의 가게를 열 수 없다."""
        token = make_preview_token('bid')
        self.assertFalse(check_preview_token('sorok', token))

    def test_a_forged_token_is_refused(self):
        self.assertFalse(check_preview_token('bid', 'bid:hand-written'))

    def test_an_empty_token_is_refused(self):
        """?preview= 만 붙여 놓은 주소로 열리면 안 된다."""
        self.assertFalse(check_preview_token('bid', ''))
        self.assertFalse(check_preview_token('bid', None))

    def test_the_lifetime_is_one_day(self):
        self.assertEqual(PREVIEW_MAX_AGE_SECONDS, 60 * 60 * 24)

    def test_an_aged_token_is_refused(self):
        """
        하루면 충분하다. 유출돼도 다음 날 죽으므로 '결제 안 하고 이 링크로
        장사하기' 가 성립하지 않는다.

        시계를 돌리는 대신 max_age 를 음수로 줘서 '이미 지났다' 를 만든다 —
        signing 이 나이를 재는 방식이 그대로 검증된다.
        """
        token = make_preview_token('bid')
        self.assertTrue(check_preview_token('bid', token))
        self.assertFalse(check_preview_token('bid', token, max_age=-1))

    def test_every_token_is_bound_to_the_secret_key(self):
        """키를 갈면 이미 뿌린 링크가 전부 죽는다. 그게 비상구다."""
        token = make_preview_token('bid')
        with self.settings(SECRET_KEY='a-completely-different-key'):
            self.assertFalse(check_preview_token('bid', token))
