"""
미리보기 토큰.

사장님이 입금 전에 자기 메뉴판을 손님이 보는 화면 그대로 확인하는 통로다.

DB 에 저장하지 않는다. django.core.signing 이 서명과 시각을 토큰 안에 넣어
주므로 만료가 저절로 오고, 회전을 사람이 눌러야 하는 문제도 없다. 저장형
토큰은 '즉시 무효화' 를 주지만 아무도 그 버튼을 누르지 않으면 링크가 영원히
산다 — 기능이 있는데 안 쓰이는 상태가 제일 나쁘다.

막으려는 것은 공격이 아니라 '결제 안 하고 이 링크로 장사하기' 이고, 그건
24시간 만료와 화면 상단 워터마크로 실용성이 사라진다.
"""

from django.core import signing

# 토큰 수명. 사장님이 하루 안에 확인하고, 유출돼도 다음 날 죽는다.
PREVIEW_MAX_AGE_SECONDS = 60 * 60 * 24

# 손님 화면 주소에 붙는 이름. 프론트 미들웨어도 같은 이름을 읽는다.
PREVIEW_QUERY_PARAM = 'preview'

# 이 소금이 다른 용도의 서명과 토큰을 갈라 놓는다. 바꾸면 이미 뿌린 링크가
# 전부 죽는다 — 그게 필요한 날의 비상구이기도 하다.
_SALT = 'menu.preview'


def make_preview_token(slug):
    """매장 하나를 24시간 동안 여는 토큰. 부를 때마다 새로 만든다."""
    return signing.dumps(slug, salt=_SALT)


def check_preview_token(slug, token, max_age=PREVIEW_MAX_AGE_SECONDS):
    """
    이 토큰이 이 매장을 지금 열어도 되는가.

    서명 안에 slug 가 들어 있으므로 남의 매장 토큰은 여기서 떨어진다.
    위조·만료·빈 값은 모두 False 다 — 호출부가 갈래를 탈 일이 없게
    예외를 밖으로 내보내지 않는다.
    """
    if not token:
        return False
    try:
        signed_slug = signing.loads(token, salt=_SALT, max_age=max_age)
    except signing.BadSignature:
        return False
    return signed_slug == slug
