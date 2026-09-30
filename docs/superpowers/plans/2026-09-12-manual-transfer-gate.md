# 계좌이체 수동 확인 게이트 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 7일 체험을 없애고, 기한 없는 무료 미리보기와 계좌이체 수동 확인 기반의 손님 공개 게이트를 만든다.

**Architecture:** 새 구독 상태를 만들지 않는다 — `unpaid` 가 곧 무료 미리보기 계정이다. 미리보기는 `django.core.signing.TimestampSigner` 로 서명한 24시간 토큰을 `?preview=` 로 받아 `SubscriptionGateMiddleware` 가 402 직전에 통과시킨다. 입금은 `PaymentRequest` 행으로 남고 Django admin 액션 하나가 `Subscription` 을 `active` 로 올린다.

**Tech Stack:** Django 5.2 / Python 3 (backend/venv), Next.js 16 App Router (frontend, JS 테스트 러너 없음 — 프론트 문구는 Django 테스트가 파일을 읽어 대조한다)

**Spec:** `docs/superpowers/specs/2026-09-12-manual-transfer-gate-design.md`

## Global Constraints

- 테스트 실행은 항상 `backend/menu_project` 에서: `../venv/bin/python manage.py test menu.<모듈> -v 2`
- **파트너 매장(`bid`·`sorok`)의 동작을 바꾸는 변경은 금지.** `status='partner'` 는 날짜를 보지 않고 무조건 통과한다. 대상을 날짜로 고르지 말고 상태로 골라라.
- `is_usable()` 은 '상태 먼저, 날짜 나중' 이다. 이 순서를 뒤집지 마라 — 날짜가 빈 신규 매장이 통과한다. `tests_subscription_gate.py` 의 `SubscriptionModelTests` 가 못박고 있다.
- 미리보기 토큰 수명: **24시간** (`PREVIEW_MAX_AGE_SECONDS = 60 * 60 * 24`)
- 계좌 정보는 코드에 박지 않는다. `BANK_NAME` · `BANK_ACCOUNT` · `BANK_HOLDER` 세 환경변수.
- 새 Discord 환경변수를 만들지 않는다. 기존 `DISCORD_WEBHOOK_URL` 을 재사용한다.
- 커밋 메시지는 한 줄 요약 + 왜 그렇게 했는지. 기존 커밋 어조를 따른다(사용자 관점의 사실, 예: `fix: 사장님이 남의 매장 메뉴를 지우고 복제할 수 있던 것`).
- 마이그레이션 번호는 `0053_owner_admin_group` 다음부터 이어진다.
- **사장님이 로그인해서 도착하는 곳은 Django `/admin/` 이다** (`auth_views.py` 가
  `redirect('admin:index')`). `/<slug>/admin/dashboard/` 는 더 이상 일상 경로가
  아니다. 사장님에게 보여야 하는 것(배너·안내·링크)을 커스텀 템플릿에만 넣으면
  **아무도 보지 못한다.** `/admin/` 첫 화면은 `admin/owner_index.html` 이고,
  거기서 매장을 정하는 것은 `owner_nav` 의 `{% owner_restaurant %}` 다.
  주문·결제·QR 만 `/<slug>/admin/` 에 남아 있고 owner_index 가 바로가기로 잇는다.

---

### Task 1: 상태 기계에서 체험을 걷어낸다

**Files:**
- Modify: `backend/menu_project/menu/models.py` (`Subscription.STATUS_CHOICES`, `TRIAL_DAYS`, `create_restaurant_settings` 시그널)
- Create: `backend/menu_project/menu/migrations/0054_remove_trialing_status.py`
- Modify: `backend/menu_project/menu/tests_subscription_gate.py` (trialing 케이스 정리)
- Delete: `backend/menu_project/menu/management/commands/expire_trials.py`
- Delete: `backend/menu_project/menu/tests_trial.py`

**Interfaces:**
- Consumes: 없음 (첫 태스크)
- Produces: 가입 직후 `Subscription.status == 'unpaid'`, `current_period_end is None`. `Subscription.STATUS_CHOICES` 에 `trialing` 이 없다. `Subscription.TRIAL_DAYS` 상수가 사라진다.

- [ ] **Step 1: 새 동작을 못박는 테스트를 쓴다**

`backend/menu_project/menu/tests_subscription_gate.py` 의 `SubscriptionModelTests` 에 추가하고, 기존 trialing 테스트 넷(`test_new_subscription_starts_a_trial`, `test_trialing_is_usable_until_the_date_passes`, `test_lapsed_trial_is_not_usable`, `test_trialing_without_a_date_is_not_usable`)은 지운다.

```python
    def test_new_restaurant_starts_unpaid_with_no_date(self):
        """
        가입은 무료 미리보기로 시작한다. 체험이 아니다.

        날짜를 채워 두면 '상태 먼저, 날짜 나중' 의 두 번째 분기로 떨어져
        손님 화면이 열린다. 무료의 경계는 미리보기까지다.
        """
        restaurant = Restaurant.objects.create(name='새 매장', slug='brand-new')
        subscription = restaurant.subscription
        self.assertEqual(subscription.status, 'unpaid')
        self.assertIsNone(subscription.current_period_end)
        self.assertFalse(subscription.is_usable())

    def test_trialing_is_no_longer_a_known_status(self):
        """체험은 폐지됐다. 상태가 남아 있으면 admin 에서 다시 고를 수 있다."""
        self.assertNotIn('trialing', dict(Subscription.STATUS_CHOICES))
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend/menu_project && ../venv/bin/python manage.py test menu.tests_subscription_gate -v 2`
Expected: FAIL — `test_new_restaurant_starts_unpaid_with_no_date` 가 `'trialing' != 'unpaid'`, `test_trialing_is_no_longer_a_known_status` 가 `'trialing' unexpectedly found`

- [ ] **Step 3: 모델을 고친다**

`menu/models.py` — `STATUS_CHOICES` 에서 `('trialing', '무료 체험'),` 줄을 지우고, 주석의 `trialing` 설명 줄도 지운다. `TRIAL_DAYS = 7` 상수와 그 주석을 지운다.

`create_restaurant_settings` 시그널을 이렇게 바꾼다.

```python
        SiteSettings.objects.create(restaurant=instance)
        # 구독 없는 매장은 게이트가 잠그므로(SubscriptionGateMiddleware) 매장이
        # 생기는 모든 경로에서 같이 만든다. 어드민에서 손으로 만들고 구독을
        # 깜빡하면 그 집 메뉴판이 이유 없이 캄캄해진다.
        #
        # unpaid 로 시작한다. 이건 '고장' 이 아니라 무료 미리보기 계정이다 —
        # 메뉴 등록과 디자인은 열려 있고, 손님 공개와 QR 만 입금 확인 뒤에 열린다.
        # 날짜를 채우지 않는 것이 중요하다. 채우면 is_usable 의 마지막 날짜
        # 분기로 떨어져 손님 화면이 공짜로 열린다.
        Subscription.objects.create(restaurant=instance, status='unpaid')
```

`from datetime import timedelta` 가 이 함수에서만 쓰였다면 import 도 함께 정리한다.

- [ ] **Step 4: 마이그레이션을 만든다**

```bash
cd backend/menu_project && ../venv/bin/python manage.py makemigrations menu --name remove_trialing_status
```

생성된 `0054_remove_trialing_status.py` 에 데이터 이행을 손으로 더한다.

```python
def trialing_becomes_unpaid(apps, schema_editor):
    """
    남아 있는 체험 매장을 미결제로 내린다.

    상태로만 고른다. 날짜로 고르면 옛 결제일을 달고 있는 파트너·해지 매장이
    딸려 들어와 영업 중인 가게가 꺼진다.
    """
    Subscription = apps.get_model('menu', 'Subscription')
    Subscription.objects.filter(status='trialing').update(
        status='unpaid', current_period_end=None
    )


def unpaid_stays_unpaid(apps, schema_editor):
    """되돌릴 것이 없다. 체험이 폐지됐으므로 trialing 으로 되살리지 않는다."""
```

`operations` 리스트의 `AlterField` **앞**에 넣는다.

```python
        migrations.RunPython(trialing_becomes_unpaid, unpaid_stays_unpaid),
```

- [ ] **Step 5: 체험 전용 코드를 지운다**

```bash
cd backend/menu_project
rm menu/management/commands/expire_trials.py
rm menu/tests_trial.py
```

`tests_subscription_gate.py` 의 `test_payment_failure_does_not_close_a_trading_store` 는 `past_due` 테스트이므로 **지우지 않는다**(이름의 'trading' 은 오타가 아니라 '영업 중' 을 뜻한다).

- [ ] **Step 6: 전체 테스트를 돌린다**

Run: `cd backend/menu_project && ../venv/bin/python manage.py test menu -v 1`
Expected: PASS. `tests_billing.py` · `tests_onboarding.py` 가 `trialing` 을 참조해 깨지면, 그 테스트가 기대하는 값을 `unpaid` 로 고친다. **`is_usable()` 의 분기 순서는 고치지 마라** — 깨졌다면 테스트가 아니라 기대값이 낡은 것이다.

- [ ] **Step 7: 커밋**

```bash
git add -A backend/menu_project/menu
git commit -m "$(cat <<'EOF'
feat: 가입하면 기한 없이 메뉴판을 만들어 볼 수 있게 한다

7일 체험을 없앤다. 가입은 unpaid 로 시작하고, 그건 고장이 아니라 무료
미리보기 계정이다. 손님 공개와 QR 만 입금 확인 뒤에 열린다.

날짜를 채우지 않는 것이 핵심이다. 채우면 is_usable 의 마지막 날짜 분기로
떨어져 손님 화면이 공짜로 열린다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GgzE1qiTaMD9V6mgF3Tyos
EOF
)"
```

---

### Task 2: 랜딩이 없는 체험을 약속하지 않게 한다

**Files:**
- Create: `backend/menu_project/menu/tests_free_tier.py`
- Modify: `frontend/src/lib/marketing-content.ts`
- Modify: `frontend/src/app/(marketing)/page.tsx`
- Modify: `frontend/src/app/(marketing)/pricing/page.tsx`
- Modify: `frontend/src/app/(marketing)/guide/page.tsx`

**Interfaces:**
- Consumes: Task 1 (`TRIAL_DAYS` 가 이미 없다)
- Produces: 가입 페이지 4곳에 `N일 무료` 문구가 없다.

- [ ] **Step 1: 방향을 뒤집은 테스트를 쓴다**

`backend/menu_project/menu/tests_free_tier.py` 를 만든다.

```python
"""
무료 티어가 화면에서 정직한가.

옛 테스트는 '랜딩이 약속한 일수 == TRIAL_DAYS' 였다. TRIAL_DAYS 를 지우면
그 테스트는 자동으로 통과해 버리고, 문구만 남아 손님이 없는 체험을
약속받는다. 그게 실제 사고라서 방향을 뒤집어 남긴다.
"""

import re
from pathlib import Path

from django.test import TestCase


class MarketingDoesNotPromiseATrialTests(TestCase):
    FRONTEND = Path(__file__).resolve().parents[3] / 'frontend' / 'src'

    # 가입 버튼이 있는 곳. 여기에 옛 문구가 남으면 손님이 속는다.
    SIGNUP_PAGES = [
        'lib/marketing-content.ts',
        'app/(marketing)/page.tsx',
        'app/(marketing)/pricing/page.tsx',
        'app/(marketing)/guide/page.tsx',
    ]

    def test_no_signup_page_promises_a_free_trial_period(self):
        for relative in self.SIGNUP_PAGES:
            with self.subTest(page=relative):
                source = (self.FRONTEND / relative).read_text(encoding='utf-8')
                promised = re.findall(r'(\d+)일(?:\s*동안)?\s*무료', source)
                self.assertEqual(
                    promised, [],
                    f'{relative} 이 아직 {promised} 일 무료 체험을 약속합니다. '
                    '체험은 폐지됐고 무료는 미리보기까지입니다.',
                )

    def test_signup_pages_say_what_is_actually_free(self):
        """
        약속을 지우기만 하면 '무료' 라는 말이 통째로 사라져 가입 유인이 없어진다.
        무엇이 무료인지는 남아 있어야 한다.
        """
        for relative in self.SIGNUP_PAGES:
            with self.subTest(page=relative):
                source = (self.FRONTEND / relative).read_text(encoding='utf-8')
                self.assertIn(
                    '미리보기', source,
                    f'{relative} 에 무료로 되는 것(미리보기) 설명이 없습니다',
                )
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend/menu_project && ../venv/bin/python manage.py test menu.tests_free_tier -v 2`
Expected: FAIL — `marketing-content.ts` 가 `['7']` 을 약속한다고 나온다

- [ ] **Step 3: 프론트 문구를 고친다**

`frontend/src/lib/marketing-content.ts` 의 해당 문단(현재 "가입하시면 7일 동안 무료로 쓰실 수 있습니다…" 로 시작하는 `p`)을 바꾼다.

```ts
    p: '가입하시면 기한 없이 메뉴판을 만들어 보실 수 있습니다. 카드도 받지 않습니다. 메뉴를 등록하고 디자인을 고치고, 미리보기 링크로 실제 화면을 확인하는 데까지 비용이 없습니다. 손님에게 공개하고 QR을 발행하실 때부터 요금이 시작됩니다.',
```

같은 파일 위쪽의 "예외가 하나 생겼다. 무료 체험 기간은 숫자로 적는다 …" 주석도 지운다 — 가리키는 대상(`TRIAL_DAYS`)이 사라졌다.

나머지 3개 `page.tsx` 에서 `N일 무료` 를 쓰는 자리를 찾아 같은 방향으로 고친다.

```bash
cd frontend && grep -rn "일 무료\|무료 체험\|7일" src/app/\(marketing\)/ src/lib/marketing-content.ts
```

각 자리를 "기한 없이 메뉴판을 만들어 보세요 · 공개는 결제 후" 취지로 바꾸고, **네 파일 모두 '미리보기' 라는 말을 포함**하게 한다.

- [ ] **Step 4: 통과를 확인한다**

Run: `cd backend/menu_project && ../venv/bin/python manage.py test menu.tests_free_tier -v 2`
Expected: PASS (2 tests)

- [ ] **Step 5: 빌드가 서지 않는지 본다**

Run: `cd frontend && npx tsc --noEmit`
Expected: 에러 없음

- [ ] **Step 6: 커밋**

```bash
git add backend/menu_project/menu/tests_free_tier.py frontend/src
git commit -m "$(cat <<'EOF'
docs: 랜딩이 없어진 체험을 약속하지 않게 한다

문구 대조 테스트의 방향을 뒤집었다. 전에는 '랜딩이 약속한 일수 ==
TRIAL_DAYS' 였는데, 상수를 지우면 그 테스트는 저절로 통과하고 문구만
남는다. 손님이 없는 체험을 약속받는 게 실제 사고다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GgzE1qiTaMD9V6mgF3Tyos
EOF
)"
```

---

### Task 3: 미리보기 토큰

**Files:**
- Create: `backend/menu_project/menu/preview.py`
- Create: `backend/menu_project/menu/tests_preview.py`

**Interfaces:**
- Consumes: 없음
- Produces:
  - `menu.preview.make_preview_token(slug: str) -> str`
  - `menu.preview.check_preview_token(slug: str, token: str) -> bool`
  - `menu.preview.PREVIEW_MAX_AGE_SECONDS: int` (= 86400)
  - `menu.preview.PREVIEW_QUERY_PARAM: str` (= `'preview'`)

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/menu_project/menu/tests_preview.py`:

```python
"""
미리보기 토큰.

사장님이 결제 전에 자기 메뉴판을 실제 화면으로 보는 통로다. 링크 하나로
열리므로, 그 링크가 곧 결제 우회로가 되지 않도록 수명과 대상이 서명에
박혀 있어야 한다.
"""

from django.core import signing
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
```

`from django.core import signing` 은 이 파일에서 더 이상 쓰지 않으므로 import 에서 뺀다.

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend/menu_project && ../venv/bin/python manage.py test menu.tests_preview -v 2`
Expected: FAIL — `ModuleNotFoundError: No module named 'menu.preview'`

- [ ] **Step 3: 구현한다**

`backend/menu_project/menu/preview.py`:

```python
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
```

- [ ] **Step 4: 통과를 확인한다**

Run: `cd backend/menu_project && ../venv/bin/python manage.py test menu.tests_preview -v 2`
Expected: PASS (6 tests)

- [ ] **Step 5: 커밋**

```bash
git add backend/menu_project/menu/preview.py backend/menu_project/menu/tests_preview.py
git commit -m "$(cat <<'EOF'
feat: 사장님이 결제 전에 자기 메뉴판을 볼 토큰을 만든다

DB 에 저장하지 않고 django.core.signing 으로 서명한다. 저장형 토큰은
즉시 무효화를 주지만 회전을 사람이 눌러야 하고, 안 누르면 링크가 영원히
산다. 기능이 있는데 아무도 안 쓰는 상태가 제일 나쁘다.

서명에 slug 가 들어가므로 한 장으로 남의 가게를 열 수 없다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GgzE1qiTaMD9V6mgF3Tyos
EOF
)"
```

---

### Task 4: 게이트가 미리보기 토큰을 통과시킨다

**Files:**
- Modify: `backend/menu_project/menu/middleware.py` (`SubscriptionGateMiddleware.process_view`)
- Modify: `backend/menu_project/menu/tests_preview.py`

**Interfaces:**
- Consumes: Task 3 (`check_preview_token`, `PREVIEW_QUERY_PARAM`)
- Produces: `?preview=<유효토큰>` 이 붙은 요청은 402 대신 통과한다. HTML 경로와 `/api/v1/` 경로 둘 다.

- [ ] **Step 1: 테스트를 더한다**

`tests_preview.py` 에 클래스를 추가한다.

```python
from django.test import TestCase, override_settings

from menu.models import Restaurant, Subscription


@override_settings(ENFORCE_SUBSCRIPTION=True)
class PreviewOpensTheGateTests(TestCase):
    def setUp(self):
        self.restaurant = Restaurant.objects.create(name='미결제 바', slug='unpaid-bar')
        # 시그널이 unpaid 로 만들어 둔다. 여기서 다시 만들지 않는다.
        self.token = make_preview_token('unpaid-bar')

    def test_unpaid_store_is_closed_without_a_token(self):
        response = self.client.get('/api/v1/restaurants/unpaid-bar/')
        self.assertEqual(response.status_code, 402)

    def test_a_valid_token_opens_the_api(self):
        response = self.client.get(f'/api/v1/restaurants/unpaid-bar/?preview={self.token}')
        self.assertEqual(response.status_code, 200)

    def test_a_valid_token_opens_the_html_page(self):
        response = self.client.get(f'/unpaid-bar/?preview={self.token}')
        self.assertNotEqual(response.status_code, 402)

    def test_another_stores_token_does_not_open_it(self):
        other = make_preview_token('some-other-bar')
        response = self.client.get(f'/api/v1/restaurants/unpaid-bar/?preview={other}')
        self.assertEqual(response.status_code, 402)

    def test_a_forged_token_does_not_open_it(self):
        response = self.client.get('/api/v1/restaurants/unpaid-bar/?preview=nope')
        self.assertEqual(response.status_code, 402)

    def test_preview_does_not_make_the_store_usable(self):
        """
        미리보기는 화면을 열어 줄 뿐 구독 상태가 아니다. 여기가 섞이면
        QR 발행과 입금 확인까지 함께 열린다.
        """
        self.assertFalse(self.restaurant.subscription.is_usable())
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend/menu_project && ../venv/bin/python manage.py test menu.tests_preview.PreviewOpensTheGateTests -v 2`
Expected: FAIL — `test_a_valid_token_opens_the_api` 가 402 를 받는다

- [ ] **Step 3: 미들웨어를 고친다**

`menu/middleware.py` 상단 import 에 더한다.

```python
from .preview import PREVIEW_QUERY_PARAM, check_preview_token
```

`process_view` 의 구독 검사 바로 뒤, 402 를 만들기 전에 넣는다.

```python
        subscription = getattr(restaurant, 'subscription', None)
        if subscription is not None and subscription.is_usable():
            return None

        # 사장님이 입금 전에 자기 화면을 확인하는 통로. 구독 상태를 바꾸지
        # 않고 이 요청 하나만 통과시킨다 — 미리보기가 '결제됨' 으로 번지면
        # QR 발행까지 열린다. 워터마크는 화면 쪽이 그린다.
        if check_preview_token(restaurant.slug, request.GET.get(PREVIEW_QUERY_PARAM)):
            return None
```

- [ ] **Step 4: 통과를 확인한다**

Run: `cd backend/menu_project && ../venv/bin/python manage.py test menu.tests_preview -v 2`
Expected: PASS (12 tests)

- [ ] **Step 5: 게이트 전체가 안 깨졌는지 본다**

Run: `cd backend/menu_project && ../venv/bin/python manage.py test menu.tests_subscription_gate -v 1`
Expected: PASS

- [ ] **Step 6: 커밋**

```bash
git add backend/menu_project/menu/middleware.py backend/menu_project/menu/tests_preview.py
git commit -m "$(cat <<'EOF'
feat: 미리보기 토큰이 있으면 게이트를 통과시킨다

구독 상태는 건드리지 않고 이 요청 하나만 연다. 미리보기가 '결제됨' 으로
번지면 QR 발행까지 같이 열린다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GgzE1qiTaMD9V6mgF3Tyos
EOF
)"
```

---

### Task 5: 미리보기 링크를 사장님에게 주고 워터마크를 씌운다

**Files:**
- Modify: `frontend/src/middleware.ts` (쿼리를 헤더로 넘긴다)
- Create: `frontend/src/components/PreviewBanner.tsx`
- Modify: `frontend/src/app/[restaurantSlug]/layout.tsx`
- Modify: `backend/menu_project/menu/admin_views.py` (`admin_dashboard` 컨텍스트)
- Modify: `backend/menu_project/menu/templates/admin/dashboard.html`
- Modify: `backend/menu_project/menu/tests_preview.py`

**Interfaces:**
- Consumes: Task 3 (`make_preview_token`), Task 4 (게이트 통과)
- Produces: 대시보드 컨텍스트에 `preview_url` (문자열). 프론트 요청 헤더에 `x-preview-token`.

- [ ] **Step 1: 대시보드가 링크를 주는지 테스트한다**

`tests_preview.py` 에 추가한다.

```python
from django.contrib.auth.models import User

from menu.models import UserProfile


class OwnerGetsAPreviewLinkTests(TestCase):
    def setUp(self):
        self.restaurant = Restaurant.objects.create(name='미결제 바', slug='unpaid-bar')
        self.user = User.objects.create_user('owner@example.com', password='pw-12345678')
        UserProfile.objects.create(user=self.user, restaurant=self.restaurant)
        self.client.force_login(self.user)

    def test_dashboard_hands_out_a_working_preview_link(self):
        response = self.client.get('/unpaid-bar/admin/dashboard/')
        self.assertEqual(response.status_code, 200)
        preview_url = response.context['preview_url']
        self.assertIn('preview=', preview_url)

        token = preview_url.split('preview=')[1]
        self.assertTrue(check_preview_token('unpaid-bar', token))

    def test_the_link_is_new_every_time(self):
        """
        저장하지 않으므로 누를 때마다 새 수명이 시작된다. 어제 열어 둔 탭의
        링크가 오늘 죽어 있어도 사장님은 다시 누르면 된다.
        """
        first = self.client.get('/unpaid-bar/admin/dashboard/').context['preview_url']
        second = self.client.get('/unpaid-bar/admin/dashboard/').context['preview_url']
        self.assertNotEqual(first, second)
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend/menu_project && ../venv/bin/python manage.py test menu.tests_preview.OwnerGetsAPreviewLinkTests -v 2`
Expected: FAIL — `KeyError: 'preview_url'`

- [ ] **Step 3: 대시보드 뷰에 링크를 넣는다**

`menu/admin_views.py` 의 `admin_dashboard` 가 템플릿에 넘기는 컨텍스트에 더한다. 파일 상단 import 에 `from .preview import make_preview_token` 을 추가하고, `settings.MARKETING_SITE_URL` 은 마케팅 사이트라 쓸 수 없으므로 손님 화면 주소를 환경변수에서 읽는다.

`menu_project/settings.py` 에 더한다(기존 `MARKETING_SITE_URL` 옆).

```python
# 손님이 실제로 보는 화면(Next.js)의 주소. 미리보기 링크를 만들 때 쓴다.
# Django 가 그리는 /<slug>/ 가 아니라 이쪽이 진짜 손님 화면이다.
CUSTOMER_SITE_URL = os.environ.get('CUSTOMER_SITE_URL', MARKETING_SITE_URL)
```

`admin_dashboard` 의 컨텍스트에:

```python
        # 누를 때마다 새로 만든다. 저장하지 않으니 회전을 신경 쓸 일이 없고,
        # 어제 열어 둔 탭의 링크가 죽어 있어도 다시 누르면 된다.
        'preview_url': (
            f'{settings.CUSTOMER_SITE_URL}/{request.restaurant.slug}'
            f'?preview={make_preview_token(request.restaurant.slug)}'
        ),
```

- [ ] **Step 4: 대시보드 화면에 버튼을 단다**

`menu/templates/admin/dashboard.html` 의 상단 액션 영역에 넣는다.

```html
        {% if not menu_is_live %}
        <a class="admin-btn admin-btn-secondary" href="{{ preview_url }}" target="_blank" rel="noopener">
            미리보기 열기
        </a>
        <button type="button" class="admin-btn admin-btn-secondary"
                onclick="navigator.clipboard.writeText('{{ preview_url }}'); this.textContent='복사됨';">
            링크 복사
        </button>
        {% endif %}
```

- [ ] **Step 5: 통과를 확인한다**

Run: `cd backend/menu_project && ../venv/bin/python manage.py test menu.tests_preview -v 2`
Expected: PASS

- [ ] **Step 6: 프론트가 토큰을 볼 수 있게 한다**

`frontend/src/middleware.ts` — layout 은 `searchParams` 를 받지 못하므로 미들웨어가 헤더로 넘긴다.

```ts
export function middleware(request: NextRequest) {
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set('x-pathname', request.nextUrl.pathname);
  // layout 은 searchParams 를 받지 못한다. 402 를 잡는 곳이 layout 이라
  // 미리보기 토큰도 거기서 보여야 해서, 쿼리를 헤더로 옮겨 준다.
  requestHeaders.set('x-preview-token', request.nextUrl.searchParams.get('preview') ?? '');

  return NextResponse.next({
    request: {
      headers: requestHeaders,
    },
  });
}
```

- [ ] **Step 7: 워터마크 컴포넌트를 만든다**

`frontend/src/components/PreviewBanner.tsx`:

```tsx
/**
 * 미리보기라는 사실을 화면에 박아 둔다.
 *
 * 닫기 버튼을 두지 않는다. 이 바가 없으면 사장님이 이 주소를 손님에게
 * 그대로 뿌려 결제 없이 장사할 수 있고, 그때 우리는 그걸 알 방법이 없다.
 */
export default function PreviewBanner() {
  return (
    <div
      style={{
        position: 'sticky',
        top: 0,
        zIndex: 9999,
        padding: '8px 16px',
        background: '#b45309',
        color: '#fff',
        fontSize: 13,
        textAlign: 'center',
      }}
    >
      미리보기입니다 · 손님에게는 아직 보이지 않습니다
    </div>
  );
}
```

- [ ] **Step 8: layout 이 바를 그리게 한다**

`frontend/src/app/[restaurantSlug]/layout.tsx` — `headers()` 는 이미 아래에서 읽고 있지만 402 분기가 그보다 **먼저** 돌므로, `headers()` 호출을 `try` 블록 위로 올린다.

```tsx
  const headerList = await headers();
  const previewToken = headerList.get('x-preview-token') || '';
  const isPreview = previewToken.length > 0;

  let restaurant: RestaurantDetail;
  let categoryTree: CategoryTree[];

  try {
    [restaurant, categoryTree] = await Promise.all([
      getRestaurant(restaurantSlug, previewToken),
      getCategoryTree(restaurantSlug, previewToken),
    ]);
  } catch (error) {
    if (isMenuClosed(error)) {
      return <MenuNotOpen />;
    }
    redirect('/');
  }
```

아래쪽의 `const headerList = await headers();` 중복 선언을 지우고, 반환하는 JSX 의 최상단에 `{isPreview && <PreviewBanner />}` 를 넣는다.

- [ ] **Step 9: API 클라이언트가 토큰을 실어 보내게 한다**

`frontend/src/lib/api.ts`:

```ts
async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}/api/v1${path}`, {
```

호출부가 토큰을 넘길 수 있도록 두 함수를 바꾼다.

```ts
/** 미리보기 토큰을 주소 뒤에 붙인다. 없으면 그대로 둔다. */
function withPreview(path: string, previewToken?: string): string {
  if (!previewToken) return path;
  const joiner = path.includes('?') ? '&' : '?';
  return `${path}${joiner}preview=${encodeURIComponent(previewToken)}`;
}

export async function getRestaurant(slug: string, previewToken?: string): Promise<RestaurantDetail> {
  return fetchAPI(withPreview(`/restaurants/${slug}/`, previewToken));
}
```

`getCategoryTree` 도 같은 모양으로 `previewToken?: string` 를 받아 `withPreview` 를 거치게 한다. 다른 호출부는 인자를 안 넘기면 그대로 동작한다.

- [ ] **Step 10: 타입 검사와 수동 확인**

Run: `cd frontend && npx tsc --noEmit`
Expected: 에러 없음

수동 확인(로컬):

```bash
# 터미널 1
cd backend/menu_project && ../venv/bin/python manage.py runserver 8010
# 터미널 2 — .env.local 이 운영을 가리키므로 반드시 덮어쓴다
cd frontend && NEXT_PUBLIC_API_URL=http://localhost:8010 npm run dev
```

`ENFORCE_SUBSCRIPTION=True` 로 띄운 뒤 미결제 매장 주소를 토큰 없이 열면 '준비 중', 대시보드에서 복사한 링크로 열면 메뉴판 + 상단 주황 바가 보여야 한다.

- [ ] **Step 11: 커밋**

```bash
git add frontend/src backend/menu_project
git commit -m "$(cat <<'EOF'
feat: 사장님에게 미리보기 링크를 주고 손님 화면에 미리보기임을 박는다

Next.js layout 은 searchParams 를 받지 못하는데 402 를 잡는 곳이 layout
이라, 미들웨어가 쿼리를 x-preview-token 헤더로 옮겨 준다.

워터마크 바에 닫기 버튼을 두지 않았다. 이 바가 없으면 사장님이 이 주소를
손님에게 뿌려 결제 없이 장사할 수 있다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GgzE1qiTaMD9V6mgF3Tyos
EOF
)"
```

---

### Task 6: QR 은 입금 확인 뒤에만 발행한다

**Files:**
- Modify: `backend/menu_project/menu/qr_views.py`
- Modify: `backend/menu_project/menu/middleware.py` (`OWNER_PREFIXES` 주석)
- Create: `backend/menu_project/menu/templates/menu/qr_locked.html`
- Create: `backend/menu_project/menu/tests_qr_gate.py`

**Interfaces:**
- Consumes: Task 1 (`unpaid` 가 기본)
- Produces: `/<slug>/qr/` 는 로그인 + 매장 권한 + `is_usable()` 셋을 모두 통과해야 QR 을 그린다.

- [ ] **Step 1: 테스트를 쓴다**

`backend/menu_project/menu/tests_qr_gate.py`:

```python
"""
QR 발행은 입금 확인 뒤다.

예전에는 QR 이 게이트의 예외였다. '결제 전에도 QR 준비까지 된다' 고
안내했기 때문인데, 방침이 뒤집혔다. 그리고 이 뷰에는 로그인 검사조차
없어서 아무나 남의 매장 QR 을 뽑을 수 있었다.
"""

from django.contrib.auth.models import User
from django.test import TestCase

from menu.models import Restaurant, UserProfile


class QrNeedsPaymentTests(TestCase):
    def setUp(self):
        self.restaurant = Restaurant.objects.create(name='미결제 바', slug='unpaid-bar')
        self.user = User.objects.create_user('owner@example.com', password='pw-12345678')
        UserProfile.objects.create(user=self.user, restaurant=self.restaurant)

    def test_anonymous_visitor_cannot_reach_the_qr_page(self):
        response = self.client.get('/unpaid-bar/qr/')
        self.assertIn(response.status_code, (302, 403))

    def test_another_owner_cannot_print_our_qr(self):
        intruder = User.objects.create_user('other@example.com', password='pw-12345678')
        other_store = Restaurant.objects.create(name='남의 바', slug='other-bar')
        UserProfile.objects.create(user=intruder, restaurant=other_store)
        self.client.force_login(intruder)

        response = self.client.get('/unpaid-bar/qr/')
        self.assertEqual(response.status_code, 403)

    def test_unpaid_owner_sees_how_to_pay_instead_of_a_qr(self):
        self.client.force_login(self.user)
        response = self.client.get('/unpaid-bar/qr/')

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'menu/qr_locked.html')
        self.assertNotContains(response, 'data:image/png;base64')

    def test_paid_owner_gets_the_qr(self):
        subscription = self.restaurant.subscription
        subscription.status = 'partner'
        subscription.save(update_fields=['status'])

        self.client.force_login(self.user)
        response = self.client.get('/unpaid-bar/qr/')

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'menu/qr_code.html')
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend/menu_project && ../venv/bin/python manage.py test menu.tests_qr_gate -v 2`
Expected: FAIL — 익명 요청이 200 을 받고, 미결제인데 `qr_code.html` 이 나온다

- [ ] **Step 3: 잠금 화면을 만든다**

`backend/menu_project/menu/templates/menu/qr_locked.html`:

```html
{% comment %}
QR 을 기다리는 사람은 사장님이다.

미들웨어의 402 화면(손님용 '준비 중')을 여기에 쓰면 안 된다. 사장님은
자기 가게가 왜 안 열리는지가 아니라 무엇을 하면 열리는지를 알아야 한다.
{% endcomment %}
{% load static %}
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QR 발행 - {{ restaurant.name }}</title>
    <link rel="stylesheet" href="{% static 'css/admin.css' %}">
</head>
<body class="brand">
    <div class="admin-container">
        <div class="admin-header">
            <h1 class="admin-title">QR 발행</h1>
            <a href="{% url 'menu:admin_dashboard' restaurant.slug %}" class="admin-btn admin-btn-secondary">대시보드로</a>
        </div>

        <div class="admin-section">
            <div class="admin-card">
                <h2>입금이 확인되면 QR이 발행됩니다</h2>
                <p>
                    QR은 손님이 메뉴판을 여는 주소를 담습니다. 지금은 그 주소가 아직
                    닫혀 있어서, QR을 인쇄해 테이블에 붙여도 손님에게는 아무것도
                    보이지 않습니다. 그래서 발행을 막아 두었습니다.
                </p>
                <p>
                    메뉴 등록과 디자인, 미리보기는 계속 무료로 쓰실 수 있습니다.
                </p>
                <a href="{% url 'menu:billing_home' restaurant.slug %}" class="admin-btn">입금 안내 보기</a>
            </div>
        </div>
    </div>
</body>
</html>
```

- [ ] **Step 4: 뷰를 고친다**

`menu/qr_views.py` 상단 import 에 더한다.

```python
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden

from .admin_views import check_restaurant_permission
```

`generate_qr_code` 를 데코레이터와 검사로 감싼다.

```python
@login_required
def generate_qr_code(request, restaurant_slug=None):
    # 이 뷰에는 원래 아무 검사도 없었다. 주소만 알면 누구나 남의 매장 QR 을
    # 뽑을 수 있었고, 그 QR 은 그 가게 메뉴판으로 곧장 들어간다.
    if not check_restaurant_permission(request.user, restaurant_slug):
        return HttpResponseForbidden("권한이 없습니다.")

    restaurant = Restaurant.objects.filter(slug=restaurant_slug).first()
    if restaurant is None:
        raise Http404

    # 게이트가 아니라 여기서 막는다. 미들웨어가 그리는 402 는 손님용 화면인데,
    # 이 페이지를 보는 사람은 사장님이다.
    subscription = getattr(restaurant, 'subscription', None)
    if subscription is None or not subscription.is_usable():
        return render(request, 'menu/qr_locked.html', {'restaurant': restaurant})

    # 현재 서버 URL 가져오기
    host = request.get_host()
```

`from django.http import Http404` 를 import 에 더한다.

- [ ] **Step 5: 미들웨어의 거짓말을 지운다**

`menu/middleware.py` 의 `OWNER_PREFIXES` 에서 `'qr/'` 를 빼고, 그 위의 주석 문단("qr/ 이 여기 있는 이유 …" 전체)을 바꾼다.

```python
    #  사장님이 되살리러 들어오는 길. 잠금 대상에서 뺀다.
    #  qr/ 은 여기 없다. QR 발행은 입금 확인 뒤이고, 그 판단과 안내 화면은
    #  qr_views 가 직접 한다 — 미들웨어가 그리는 402 는 손님용이라 사장님이
    #  무엇을 하면 열리는지 알 수 없다.
    OWNER_PREFIXES = ('admin/', 'api/v1/contact')
```

- [ ] **Step 6: 통과를 확인한다**

Run: `cd backend/menu_project && ../venv/bin/python manage.py test menu.tests_qr_gate menu.tests_subscription_gate -v 2`
Expected: PASS. `tests_subscription_gate.py` 의 `test_owner_can_still_get_the_qr_before_paying` 는 방침이 뒤집혔으므로 지운다 — 그 자리를 `tests_qr_gate.py` 가 대신한다.

- [ ] **Step 7: 커밋**

```bash
git add backend/menu_project/menu
git commit -m "$(cat <<'EOF'
feat: QR 은 입금 확인 뒤에만 발행한다

게이트가 아니라 뷰에서 막는다. 미들웨어가 그리는 402 는 손님용 '준비 중'
화면인데, QR 페이지를 보는 사람은 사장님이라 무엇을 하면 열리는지 알 수 없다.

덤으로 이 뷰에 로그인·권한 검사를 붙였다. 지금까지 주소만 알면 아무나
남의 매장 QR 을 뽑을 수 있었다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GgzE1qiTaMD9V6mgF3Tyos
EOF
)"
```

---

### Task 7: 온보딩 체크리스트와 배너의 문구를 방침에 맞춘다

**Files:**
- Modify: `backend/menu_project/menu/onboarding_views.py` (`onboarding_home` 의 `steps`)
- Modify: `backend/menu_project/menu/templates/admin/_payment_banner.html`
- Modify: `backend/menu_project/menu/templates/admin/owner_index.html` (배너를 여기에도)
- Modify: `backend/menu_project/menu/templatetags/owner_nav.py` (배너가 쓸 상태)
- Modify: `backend/menu_project/menu/tests_onboarding.py`
- Modify: `backend/menu_project/menu/tests_preview.py`

**배너는 Django `/admin/` 에도 떠야 한다.** 사장님이 로그인해서 도착하는 곳이
거기다. 커스텀 템플릿(dashboard·start)에만 넣으면 이 기능에서 제일 중요한
문장("아직 공개되지 않았습니다")을 아무도 보지 못한다. 아래 Step 4 에서 같은
`_payment_banner.html` 을 `owner_index.html` 에도 include 하고, 거기서 쓸
`menu_is_live`·`subscription`·`billing_url` 을 `owner_nav` 태그로 넘긴다
(owner_index 는 뷰가 우리 것이 아니라 컨텍스트를 직접 못 넣는다).

또한 Task 1 에서 이쪽으로 미뤄 둔 테스트가 있다 — 가입만 한 매장이 '닫혔다'
는 말을 듣지 않는지 보는 것이다. Step 1 에 포함한다.

**Interfaces:**
- Consumes: Task 1, Task 5 (`preview_url`), Task 6 (QR 잠금)
- Produces: 체크리스트의 `qr` 단계가 미결제면 잠긴다. 배너가 체험이 아니라 무료 미리보기를 설명한다.

- [ ] **Step 1: 테스트를 더한다**

`tests_onboarding.py` 에 추가한다.

```python
    def test_qr_step_is_locked_until_payment(self):
        """
        체크리스트가 'QR 받기' 를 열어 두면 사장님은 거기까지 갔다가 잠긴
        화면을 만난다. 잠긴 것은 잠겼다고 먼저 말해야 한다.
        """
        response = self.client.get(f'/{self.restaurant.slug}/admin/start/')
        qr_step = next(s for s in response.context['steps'] if s['key'] == 'qr')
        self.assertTrue(qr_step['locked'])
        self.assertIn('입금', qr_step['detail'])

    def test_checklist_offers_a_preview_before_payment(self):
        response = self.client.get(f'/{self.restaurant.slug}/admin/start/')
        self.assertIn('preview=', response.context['preview_url'])
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend/menu_project && ../venv/bin/python manage.py test menu.tests_onboarding -v 2`
Expected: FAIL — `qr_step['locked']` 가 False, `preview_url` 이 컨텍스트에 없음

- [ ] **Step 3: 체크리스트를 고친다**

`menu/onboarding_views.py` 의 `onboarding_home` 에서 `from .preview import make_preview_token` 을 import 하고, `qr` 단계를 바꾼다.

```python
        {
            'key': 'qr',
            'title': 'QR 받기',
            # QR 은 내려받아도 DB 에 흔적이 남지 않아 완료로 표시할 근거가 없다.
            'done': False,
            # 메뉴가 없어도, 입금 확인 전이어도 잠긴다. 둘 중 먼저 걸리는 쪽을
            # 이유로 말해 준다 — '왜 잠겼는지' 가 다르면 할 일도 다르다.
            'locked': menu_count == 0 or not paid,
            'detail': (
                '메뉴를 먼저 등록하면 QR이 의미가 생깁니다.' if menu_count == 0
                else '입금이 확인되면 QR을 발행해 드립니다. 그전까지는 미리보기로 확인하세요.'
                if not paid
                else '테이블에 붙일 QR을 내려받으세요.'
            ),
            'primary_url': reverse('menu:qr_code', kwargs={'restaurant_slug': restaurant.slug}),
            'primary_label': 'QR 코드 보기',
        },
```

같은 함수의 렌더 컨텍스트에 더한다.

```python
        'preview_url': (
            f'{settings.CUSTOMER_SITE_URL}/{restaurant.slug}'
            f'?preview={make_preview_token(restaurant.slug)}'
        ),
```

- [ ] **Step 4: 배너를 고친다**

`menu/templates/admin/_payment_banner.html` 전체를 바꾼다.

```html
{% comment %}
사장님에게 손님 화면의 상태를 알린다.

체험이 폐지되면서 알릴 상태가 둘로 줄었다. 아직 공개 전(무료 미리보기)과,
공개했다가 기간이 끝난 것이다. 둘을 한 문구로 뭉치면 전자가 '닫혔다' 는
말을 듣고 고장인 줄 안다.
{% endcomment %}
{% if not menu_is_live %}
    {% if subscription.status == 'unpaid' and not subscription.current_period_end %}
    <div class="payment-banner">
        <div class="payment-banner-text">
            <strong>아직 손님에게 공개되지 않았습니다</strong>
            <span>메뉴 등록과 디자인은 기한 없이 무료입니다. 미리보기로 실제 화면을 확인하시고, 공개할 준비가 되시면 입금 안내를 눌러 주세요.</span>
        </div>
        <a class="payment-banner-btn" href="{{ billing_url }}">입금 안내 보기</a>
    </div>
    {% else %}
    <div class="payment-banner">
        <div class="payment-banner-text">
            <strong>이용 기간이 끝나 손님 화면이 닫혔습니다</strong>
            <span>지금은 손님이 메뉴판 주소로 들어와도 메뉴가 보이지 않습니다. 관리 화면과 등록하신 메뉴는 그대로 남아 있습니다.</span>
        </div>
        <a class="payment-banner-btn" href="{{ billing_url }}">연장 입금 안내</a>
    </div>
    {% endif %}
{% endif %}
```

이 템플릿을 include 하는 화면들이 `billing_url` 을 넘기도록, 넘기는 뷰(`admin_dashboard`, `onboarding_home`)의 컨텍스트에 더한다.

```python
        'billing_url': reverse('menu:billing_home', kwargs={'restaurant_slug': restaurant.slug}),
```

`contact_url` 은 더 이상 쓰이지 않으면 함께 지운다.

- [ ] **Step 5: 통과를 확인한다**

Run: `cd backend/menu_project && ../venv/bin/python manage.py test menu.tests_onboarding -v 2`
Expected: PASS

- [ ] **Step 6: 커밋**

```bash
git add backend/menu_project/menu
git commit -m "$(cat <<'EOF'
fix: 체크리스트와 배너가 이제 못 하는 일을 권하던 것

'QR 받기' 가 열려 있어서 사장님이 거기까지 갔다가 잠긴 화면을 만났다.
배너는 없어진 체험을 계속 설명하고 있었다. 잠긴 것은 잠겼다고 먼저 말한다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GgzE1qiTaMD9V6mgF3Tyos
EOF
)"
```

---

### Task 8: PaymentRequest 모델

**Files:**
- Modify: `backend/menu_project/menu/models.py`
- Create: `backend/menu_project/menu/migrations/0055_paymentrequest.py`
- Create: `backend/menu_project/menu/tests_payment_request.py`

**Interfaces:**
- Consumes: Task 1
- Produces:
  - `menu.models.PaymentRequest` — 필드 `restaurant`(FK, related_name=`payment_requests`), `plan`, `depositor_name`, `amount`, `status`, `note`, `created_at`, `confirmed_at`, `confirmed_by`
  - `PaymentRequest.STATUS_CHOICES` = pending / confirmed / rejected
  - `PaymentRequest.confirm(months: int, user) -> Subscription` — 구독을 `active` 로 올리고 기간을 더한다

- [ ] **Step 1: 테스트를 쓴다**

`backend/menu_project/menu/tests_payment_request.py`:

```python
"""
입금 신청과 확인.

통장에는 입금자명만 찍힌다. 그 이름을 매장에 이어 붙일 근거가 화면
어딘가에 남아 있어야, 나중에 '냈다/안 냈다' 가 갈릴 때 볼 것이 있다.
"""

from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from menu.models import PaymentRequest, Restaurant, Subscription


class ConfirmingAPaymentOpensTheStoreTests(TestCase):
    def setUp(self):
        self.restaurant = Restaurant.objects.create(name='미결제 바', slug='unpaid-bar')
        self.staff = User.objects.create_user('me@example.com', password='pw-12345678', is_staff=True)
        self.request = PaymentRequest.objects.create(
            restaurant=self.restaurant,
            plan='entry',
            depositor_name='홍길동',
            amount=9900,
        )

    def test_a_new_request_waits(self):
        self.assertEqual(self.request.status, 'pending')

    def test_confirming_turns_the_subscription_on(self):
        self.request.confirm(months=1, user=self.staff)

        subscription = Restaurant.objects.get(slug='unpaid-bar').subscription
        self.assertEqual(subscription.status, 'active')
        self.assertTrue(subscription.is_usable())

    def test_confirming_records_who_and_when(self):
        self.request.confirm(months=1, user=self.staff)
        self.request.refresh_from_db()

        self.assertEqual(self.request.status, 'confirmed')
        self.assertEqual(self.request.confirmed_by, self.staff)
        self.assertIsNotNone(self.request.confirmed_at)

    def test_a_month_is_added_from_today_when_nothing_is_running(self):
        before = timezone.now()
        self.request.confirm(months=1, user=self.staff)

        until = self.restaurant.subscription.access_until
        self.assertGreater(until, before + timedelta(days=27))
        self.assertLess(until, before + timedelta(days=33))

    def test_paying_early_does_not_eat_the_remaining_days(self):
        """
        만료 전에 미리 낸 사람의 남은 날을 먹으면 안 된다. 오늘부터 한 달이
        아니라 '기존 만료일부터' 한 달이다.
        """
        subscription = self.restaurant.subscription
        subscription.status = 'active'
        subscription.current_period_end = timezone.now() + timedelta(days=20)
        subscription.save(update_fields=['status', 'current_period_end'])

        self.request.confirm(months=1, user=self.staff)

        until = self.restaurant.subscription.access_until
        self.assertGreater(until, timezone.now() + timedelta(days=45))

    def test_an_expired_period_restarts_from_today(self):
        """기간이 이미 지났으면 과거에 더해 봐야 여전히 과거다."""
        subscription = self.restaurant.subscription
        subscription.status = 'active'
        subscription.current_period_end = timezone.now() - timedelta(days=40)
        subscription.save(update_fields=['status', 'current_period_end'])

        self.request.confirm(months=1, user=self.staff)

        self.assertTrue(self.restaurant.subscription.is_usable())

    def test_three_months_is_three_months(self):
        self.request.confirm(months=3, user=self.staff)
        until = self.restaurant.subscription.access_until
        self.assertGreater(until, timezone.now() + timedelta(days=85))

    def test_confirming_twice_does_not_stack(self):
        """
        같은 신청을 두 번 눌러도 기간이 두 배가 되면 안 된다. 목록에서
        두 번 클릭하는 일은 실제로 일어난다.
        """
        self.request.confirm(months=1, user=self.staff)
        first = self.restaurant.subscription.access_until

        self.request.confirm(months=1, user=self.staff)
        self.assertEqual(self.restaurant.subscription.access_until, first)
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend/menu_project && ../venv/bin/python manage.py test menu.tests_payment_request -v 2`
Expected: FAIL — `ImportError: cannot import name 'PaymentRequest'`

- [ ] **Step 3: 모델을 쓴다**

`menu/models.py` 의 `Subscription` 클래스 아래에 더한다.

```python
class PaymentRequest(models.Model):
    """
    사장님이 "입금했습니다" 하고 남기는 줄.

    통장에는 입금자명만 찍힌다. 상호와 다른 경우가 대부분이라, 그 이름을
    매장에 이어 붙일 근거가 없으면 누가 보낸 돈인지 알 수 없다. 이 모델이
    그 근거다.

    상태를 바꾸는 일은 confirm() 하나로 모은다. admin 액션이 네 개(1·3·6·12
    개월)지만 하는 일은 기간만 다르고 같다.
    """

    STATUS_CHOICES = [
        ('pending', '확인 대기'),
        ('confirmed', '확인됨'),
        ('rejected', '반려'),
    ]

    restaurant = models.ForeignKey(
        Restaurant, on_delete=models.CASCADE,
        related_name='payment_requests', verbose_name="매장",
    )
    plan = models.CharField(max_length=20, choices=Subscription.PLAN_CHOICES, verbose_name="요금제")
    depositor_name = models.CharField(max_length=50, verbose_name="입금자명")
    amount = models.PositiveIntegerField(verbose_name="입금액")
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="상태",
    )
    note = models.TextField(blank=True, default='', verbose_name="메모")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="신청 일시")
    confirmed_at = models.DateTimeField(null=True, blank=True, verbose_name="확인 일시")
    confirmed_by = models.ForeignKey(
        'auth.User', null=True, blank=True, on_delete=models.SET_NULL,
        verbose_name="확인한 사람",
    )

    class Meta:
        verbose_name = "입금 신청"
        verbose_name_plural = "입금 신청 목록"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.restaurant.name} · {self.depositor_name} · {self.amount:,}원"

    def confirm(self, months, user):
        """
        입금을 확인하고 매장을 연다.

        기존 만료일이 남아 있으면 거기에 더한다. 오늘부터 세면 만료 전에
        미리 낸 사람의 남은 날을 먹는다. 반대로 이미 지난 만료일에 더하면
        여전히 과거라서, 둘 중 나중 것을 기준으로 잡는다.

        이미 확인된 신청은 아무것도 하지 않는다 — 목록에서 두 번 누르는
        일이 실제로 일어나고, 그때 기간이 두 배가 되면 안 된다.

        한 달은 달력이 아니라 30일이다. dateutil 을 얹지 않으려고 그랬다 —
        청구가 수동이라 며칠 오차는 문제가 되지 않고, RAM 1GB 미만인 운영
        인스턴스에 패키지를 하나 더 얹는 값이 더 비싸다.
        """
        if self.status == 'confirmed':
            return self.restaurant.subscription

        now = timezone.now()
        subscription = self.restaurant.subscription
        base = subscription.current_period_end
        if base is None or base < now:
            base = now

        subscription.status = 'active'
        subscription.plan = self.plan
        subscription.current_period_end = base + timedelta(days=30 * months)
        subscription.save(update_fields=['status', 'plan', 'current_period_end', 'updated_at'])

        self.status = 'confirmed'
        self.confirmed_at = now
        self.confirmed_by = user
        self.save(update_fields=['status', 'confirmed_at', 'confirmed_by'])
        return subscription
```

파일 상단에 `from datetime import timedelta` 와 `from django.utils import timezone` 이 있는지 확인하고 없으면 더한다. `dateutil` 은 의존성에 없으니 쓰지 않는다.

- [ ] **Step 4: 마이그레이션**

```bash
cd backend/menu_project && ../venv/bin/python manage.py makemigrations menu --name paymentrequest
```

- [ ] **Step 5: 통과를 확인한다**

Run: `cd backend/menu_project && ../venv/bin/python manage.py test menu.tests_payment_request -v 2`
Expected: PASS (8 tests)

- [ ] **Step 6: 커밋**

```bash
git add backend/menu_project/menu
git commit -m "$(cat <<'EOF'
feat: 입금 신청을 줄로 남긴다

통장에는 입금자명만 찍히고 상호와 다른 경우가 대부분이다. 그 이름을
매장에 이어 붙일 근거가 없으면 누가 보낸 돈인지 알 수 없다.

확인은 기존 만료일에 더한다. 오늘부터 세면 만료 전에 미리 낸 사람의
남은 날을 먹는다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GgzE1qiTaMD9V6mgF3Tyos
EOF
)"
```

---

### Task 9: 입금 신청 폼과 알림

**Files:**
- Modify: `backend/menu_project/menu/billing_views.py`
- Modify: `backend/menu_project/menu/templates/admin/billing.html`
- Modify: `backend/menu_project/menu/urls.py`
- Modify: `backend/menu_project/menu/notifications.py`
- Modify: `backend/menu_project/menu_project/settings.py`
- Modify: `backend/menu_project/menu/tests_payment_request.py`

**Interfaces:**
- Consumes: Task 8 (`PaymentRequest`)
- Produces:
  - URL `menu:billing_request` = `/<slug>/admin/billing/request/` (POST)
  - `notifications.build_payment_request_payload(payment_request) -> dict`
  - `notifications.send_payment_request_notification(payment_request)`
  - settings: `BANK_NAME`, `BANK_ACCOUNT`, `BANK_HOLDER`

- [ ] **Step 1: 테스트를 더한다**

`tests_payment_request.py` 에 클래스를 추가한다.

```python
from menu.models import UserProfile


class OwnerSubmitsAPaymentRequestTests(TestCase):
    def setUp(self):
        self.restaurant = Restaurant.objects.create(name='미결제 바', slug='unpaid-bar')
        self.user = User.objects.create_user('owner@example.com', password='pw-12345678')
        UserProfile.objects.create(user=self.user, restaurant=self.restaurant)
        self.client.force_login(self.user)

    def test_submitting_creates_a_pending_request(self):
        response = self.client.post('/unpaid-bar/admin/billing/request/', {
            'depositor_name': '홍길동',
            'plan': 'entry',
        })
        self.assertEqual(response.status_code, 302)

        request = PaymentRequest.objects.get(restaurant=self.restaurant)
        self.assertEqual(request.depositor_name, '홍길동')
        self.assertEqual(request.amount, Subscription.PLAN_PRICES['entry'])
        self.assertEqual(request.status, 'pending')

    def test_the_amount_comes_from_the_server_not_the_form(self):
        """
        금액을 폼에서 받으면 사장님이 1원을 보내고 1원이라고 적을 수 있다.
        요금제만 받고 금액은 서버가 정한다.
        """
        self.client.post('/unpaid-bar/admin/billing/request/', {
            'depositor_name': '홍길동',
            'plan': 'pro',
            'amount': '1',
        })
        request = PaymentRequest.objects.get(restaurant=self.restaurant)
        self.assertEqual(request.amount, Subscription.PLAN_PRICES['pro'])

    def test_a_second_request_is_refused_while_one_is_waiting(self):
        """같은 입금이 두 줄로 남으면 통장과 대조할 때 헷갈린다."""
        payload = {'depositor_name': '홍길동', 'plan': 'entry'}
        self.client.post('/unpaid-bar/admin/billing/request/', payload)
        self.client.post('/unpaid-bar/admin/billing/request/', payload)

        self.assertEqual(PaymentRequest.objects.filter(restaurant=self.restaurant).count(), 1)

    def test_an_empty_depositor_name_is_refused(self):
        self.client.post('/unpaid-bar/admin/billing/request/', {
            'depositor_name': '   ',
            'plan': 'entry',
        })
        self.assertEqual(PaymentRequest.objects.count(), 0)

    def test_another_owner_cannot_submit_for_our_store(self):
        intruder = User.objects.create_user('other@example.com', password='pw-12345678')
        other = Restaurant.objects.create(name='남의 바', slug='other-bar')
        UserProfile.objects.create(user=intruder, restaurant=other)
        self.client.force_login(intruder)

        response = self.client.post('/unpaid-bar/admin/billing/request/', {
            'depositor_name': '나쁜사람', 'plan': 'entry',
        })
        self.assertEqual(response.status_code, 403)
        self.assertEqual(PaymentRequest.objects.count(), 0)


class PaymentRequestNotificationTests(TestCase):
    def setUp(self):
        self.restaurant = Restaurant.objects.create(name='미결제 바', slug='unpaid-bar')
        self.user = User.objects.create_user('owner@example.com', password='pw-12345678')
        UserProfile.objects.create(user=self.user, restaurant=self.restaurant)
        self.request = PaymentRequest.objects.create(
            restaurant=self.restaurant, plan='entry',
            depositor_name='홍길동', amount=9900,
        )

    def test_payload_carries_what_we_need_to_match_the_bank_line(self):
        from menu.notifications import build_payment_request_payload

        payload = build_payment_request_payload(self.request)
        text = str(payload)

        self.assertIn('홍길동', text)
        self.assertIn('9,900', text)
        self.assertIn('unpaid-bar', text)
        self.assertIn('owner@example.com', text)
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend/menu_project && ../venv/bin/python manage.py test menu.tests_payment_request -v 2`
Expected: FAIL — 404 (URL 없음), `ImportError: build_payment_request_payload`

- [ ] **Step 3: 설정에 계좌를 더한다**

`menu_project/settings.py` 의 `SUPPORT_EMAIL` 근처에:

```python
# 계좌이체로 받는다. 코드에 박으면 계좌를 바꿀 때 배포를 해야 한다.
BANK_NAME = os.environ.get('BANK_NAME', '')
BANK_ACCOUNT = os.environ.get('BANK_ACCOUNT', '')
BANK_HOLDER = os.environ.get('BANK_HOLDER', '')
```

- [ ] **Step 4: 알림을 더한다**

`menu/notifications.py` 에 추가한다. 기존 `build_trial_expired_payload` 는 Task 11 에서 이름이 바뀌므로 여기서는 건드리지 않는다.

```python
def build_payment_request_payload(payment_request):
    """입금 신청을 Discord 웹훅 JSON 페이로드로 변환한다."""
    restaurant = payment_request.restaurant
    email, phone = _owner_contact(restaurant)
    return {
        "embeds": [
            {
                "title": "💰 입금 신청 — 통장을 확인해 주세요",
                "description": "확인되면 Django admin 의 '입금 신청' 에서 기간을 골라 확인하세요.",
                "color": 3447003,
                "fields": [
                    {"name": "매장명", "value": restaurant.name or "-", "inline": True},
                    {"name": "주소", "value": f"/{restaurant.slug}", "inline": True},
                    {"name": "입금자명", "value": payment_request.depositor_name, "inline": True},
                    {"name": "금액", "value": f"{payment_request.amount:,}원", "inline": True},
                    {"name": "요금제", "value": payment_request.get_plan_display(), "inline": True},
                    {"name": "이메일", "value": email, "inline": False},
                    {"name": "연락처", "value": phone, "inline": True},
                ],
            }
        ]
    }


def send_payment_request_notification(payment_request):
    """입금 신청 알림을 비동기로 발송한다. 웹훅이 없으면 아무것도 하지 않는다."""
    return _send(build_payment_request_payload(payment_request))
```

- [ ] **Step 5: 뷰와 URL 을 더한다**

`menu/urls.py` 의 billing 묶음에:

```python
    path('admin/billing/request/', billing_views.submit_payment_request, name='billing_request'),
```

`menu/billing_views.py` 에:

```python
@login_required
@require_POST
def submit_payment_request(request, restaurant_slug=None):
    """
    "입금했습니다" 를 줄로 남기고 우리에게 알린다.

    금액은 폼에서 받지 않는다. 받으면 1원을 보내고 1원이라고 적을 수 있다.
    요금제만 받고 금액은 PLAN_PRICES 가 정한다 — 요금 페이지에 적힌 값과
    여기가 갈리면 그 자체가 사고다.
    """
    if not check_restaurant_permission(request.user, restaurant_slug):
        return HttpResponseForbidden("권한이 없습니다.")

    restaurant = request.restaurant
    depositor_name = (request.POST.get('depositor_name') or '').strip()
    plan = request.POST.get('plan') or ''

    if not depositor_name:
        messages.error(request, '입금자명을 입력해 주세요. 통장에 찍힌 이름과 같아야 합니다.')
        return redirect('menu:billing_home', restaurant_slug=restaurant.slug)

    if plan not in Subscription.PLAN_PRICES:
        messages.error(request, '요금제를 골라 주세요.')
        return redirect('menu:billing_home', restaurant_slug=restaurant.slug)

    # 대기 중인 신청이 있으면 또 만들지 않는다. 같은 입금이 두 줄로 남으면
    # 통장과 대조할 때 어느 쪽이 진짜인지 알 수 없다.
    if PaymentRequest.objects.filter(restaurant=restaurant, status='pending').exists():
        messages.info(request, '이미 확인을 기다리는 신청이 있습니다. 확인되면 알려 드리겠습니다.')
        return redirect('menu:billing_home', restaurant_slug=restaurant.slug)

    payment_request = PaymentRequest.objects.create(
        restaurant=restaurant,
        plan=plan,
        depositor_name=depositor_name,
        amount=Subscription.PLAN_PRICES[plan],
    )
    notifications.send_payment_request_notification(payment_request)

    messages.success(
        request,
        '입금 신청을 받았습니다. 통장을 확인하는 대로 손님 화면과 QR을 열어 드리겠습니다.',
    )
    return redirect('menu:billing_home', restaurant_slug=restaurant.slug)
```

import 에 `from . import notifications` 와 `from .models import PaymentRequest, Subscription` 을 맞춘다.

`billing_home` 의 컨텍스트에 더한다.

```python
        'bank_name': settings.BANK_NAME,
        'bank_account': settings.BANK_ACCOUNT,
        'bank_holder': settings.BANK_HOLDER,
        'pending_request': PaymentRequest.objects.filter(
            restaurant=request.restaurant, status='pending',
        ).first(),
```

- [ ] **Step 6: 결제 화면에 폼을 단다**

`menu/templates/admin/billing.html` 의 "결제 연동을 준비하고 있습니다" 블록(`{% if not payment_configured %}` … `{% endif %}`)을 계좌 안내와 폼으로 바꾼다.

```html
        {% if pending_request %}
        <div class="admin-section">
            <div class="admin-card">
                <h2>확인 중입니다</h2>
                <p>
                    <strong>{{ pending_request.depositor_name }}</strong> 이름으로
                    {{ pending_request.amount|floatformat:0 }}원 입금 신청을 받았습니다.
                    통장을 확인하는 대로 손님 화면과 QR을 열어 드리겠습니다.
                </p>
            </div>
        </div>
        {% else %}
        <div class="admin-section">
            <div class="admin-card">
                <h2>입금 안내</h2>
                {% if bank_account %}
                <p>
                    {{ bank_name }} {{ bank_account }} (예금주 {{ bank_holder }})
                </p>
                <p>
                    입금하신 뒤 아래에 <strong>통장에 찍힐 이름</strong>을 적어 주세요.
                    상호와 달라도 괜찮습니다 — 그 이름으로 대조합니다.
                </p>
                <form method="post" action="{% url 'menu:billing_request' request.restaurant.slug %}">
                    {% csrf_token %}
                    <label for="depositor_name">입금자명</label>
                    <input type="text" id="depositor_name" name="depositor_name" maxlength="50" required>

                    <label for="plan">요금제</label>
                    <select id="plan" name="plan">
                        {% for plan in plans %}
                        <option value="{{ plan.value }}" {% if plan.current %}selected{% endif %}>
                            {{ plan.label }} · 월 {{ plan.price }}원
                        </option>
                        {% endfor %}
                    </select>

                    <button type="submit" class="admin-btn">입금했습니다</button>
                </form>
                {% else %}
                <p>계좌 정보가 아직 설정되지 않았습니다. 잠시 후 다시 시도해 주세요.</p>
                {% endif %}
            </div>
        </div>
        {% endif %}
```

- [ ] **Step 7: 통과를 확인한다**

Run: `cd backend/menu_project && ../venv/bin/python manage.py test menu.tests_payment_request menu.tests_billing -v 2`
Expected: PASS

- [ ] **Step 8: 커밋**

```bash
git add backend/menu_project
git commit -m "$(cat <<'EOF'
feat: 사장님이 입금했다고 알리고 우리가 통장과 대조한다

금액은 폼에서 받지 않는다. 받으면 1원을 보내고 1원이라고 적을 수 있다.
요금제만 받고 금액은 PLAN_PRICES 가 정한다.

대기 중인 신청이 있으면 또 만들지 않는다. 같은 입금이 두 줄로 남으면
통장과 대조할 때 어느 쪽이 진짜인지 알 수 없다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GgzE1qiTaMD9V6mgF3Tyos
EOF
)"
```

---

### Task 10: Django admin 에서 한 번에 확인한다

**Files:**
- Modify: `backend/menu_project/menu/admin.py`
- Modify: `backend/menu_project/menu/tests_payment_request.py`

**Interfaces:**
- Consumes: Task 8 (`PaymentRequest.confirm`)
- Produces: admin 에 `PaymentRequest` 와 `Subscription` 이 등록되고, 액션 4개(`confirm_1`, `confirm_3`, `confirm_6`, `confirm_12`)가 붙는다.

- [ ] **Step 1: 테스트를 더한다**

```python
from django.contrib.admin.sites import site as admin_site

from menu.admin import PaymentRequestAdmin


class PaymentRequestAdminTests(TestCase):
    def setUp(self):
        self.restaurant = Restaurant.objects.create(name='미결제 바', slug='unpaid-bar')
        self.staff = User.objects.create_superuser('me@example.com', password='pw-12345678')
        self.request = PaymentRequest.objects.create(
            restaurant=self.restaurant, plan='entry',
            depositor_name='홍길동', amount=9900,
        )

    def test_subscription_is_reachable_from_admin(self):
        """
        알림을 받고 손으로 partner 로 바꾸거나 기간을 미루려면 admin 에
        있어야 한다. 지금까지 등록조차 되어 있지 않았다.
        """
        from menu.models import Subscription
        self.assertIn(Subscription, admin_site._registry)

    def test_one_click_opens_the_store_for_a_month(self):
        from django.test import RequestFactory

        admin = PaymentRequestAdmin(PaymentRequest, admin_site)
        http_request = RequestFactory().post('/admin/')
        http_request.user = self.staff
        # 메시지 프레임워크가 없는 요청이라 admin 액션이 message_user 에서
        # 터지지 않도록 스텁을 끼운다.
        http_request._messages = []
        admin.message_user = lambda *args, **kwargs: None

        admin.confirm_1(http_request, PaymentRequest.objects.filter(pk=self.request.pk))

        subscription = Restaurant.objects.get(slug='unpaid-bar').subscription
        self.assertEqual(subscription.status, 'active')
        self.assertTrue(subscription.is_usable())
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend/menu_project && ../venv/bin/python manage.py test menu.tests_payment_request.PaymentRequestAdminTests -v 2`
Expected: FAIL — `ImportError: cannot import name 'PaymentRequestAdmin'`

- [ ] **Step 3: admin 을 쓴다**

`menu/admin.py` 끝에 더한다. import 에 `PaymentRequest, Subscription` 을 추가한다.

```python
@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    """
    구독을 손으로 볼 자리.

    지금까지 등록되어 있지 않아서, 알림을 받고도 partner 로 바꾸거나
    기간을 미루려면 shell 을 열어야 했다.
    """
    list_display = ('restaurant', 'status', 'plan', 'current_period_end', 'photo_import_count')
    list_filter = ('status', 'plan')
    search_fields = ('restaurant__name', 'restaurant__slug')
    autocomplete_fields = ('restaurant',)


@admin.register(PaymentRequest)
class PaymentRequestAdmin(admin.ModelAdmin):
    """
    통장과 대조하는 자리.

    확인 액션이 넷이지만 하는 일은 기간만 다르고 같다. 기간 입력 페이지를
    따로 거치게 하면 대조하다 말고 화면을 하나 더 넘겨야 해서, 목록에서
    바로 끝나게 했다.
    """
    list_display = ('created_at', 'restaurant', 'depositor_name', 'amount', 'plan', 'status')
    list_filter = ('status', 'plan')
    search_fields = ('depositor_name', 'restaurant__name', 'restaurant__slug')
    readonly_fields = ('created_at', 'confirmed_at', 'confirmed_by')
    actions = ('confirm_1', 'confirm_3', 'confirm_6', 'confirm_12')

    def _confirm(self, request, queryset, months):
        opened = 0
        for payment_request in queryset:
            payment_request.confirm(months=months, user=request.user)
            opened += 1
        self.message_user(request, f'{opened}건을 {months}개월로 확인했습니다.')

    @admin.action(description='입금 확인 · 1개월')
    def confirm_1(self, request, queryset):
        self._confirm(request, queryset, 1)

    @admin.action(description='입금 확인 · 3개월')
    def confirm_3(self, request, queryset):
        self._confirm(request, queryset, 3)

    @admin.action(description='입금 확인 · 6개월')
    def confirm_6(self, request, queryset):
        self._confirm(request, queryset, 6)

    @admin.action(description='입금 확인 · 1년')
    def confirm_12(self, request, queryset):
        self._confirm(request, queryset, 12)
```

`SubscriptionAdmin.autocomplete_fields` 가 동작하려면 `RestaurantAdmin` 에 `search_fields` 가 있어야 한다. 없으면 `search_fields = ('name', 'slug')` 를 더한다.

`photo_import_count` 는 Task 12 에서 생긴다. 그 전까지는 `list_display` 에서 빼 두고 Task 12 에서 다시 넣는다.

- [ ] **Step 4: 통과를 확인한다**

Run: `cd backend/menu_project && ../venv/bin/python manage.py test menu.tests_payment_request -v 2`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add backend/menu_project/menu
git commit -m "$(cat <<'EOF'
feat: 입금을 admin 에서 한 번에 확인한다

기간 입력 페이지를 따로 두지 않고 액션 넷(1·3·6·12개월)으로 끝낸다.
통장을 대조하다 말고 화면을 하나 더 넘기게 하고 싶지 않았다.

구독도 함께 등록했다. 지금까지 등록되어 있지 않아서 partner 로 바꾸거나
기간을 미루려면 shell 을 열어야 했다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GgzE1qiTaMD9V6mgF3Tyos
EOF
)"
```

---

### Task 11: 만료 스윕

**Files:**
- Create: `backend/menu_project/menu/management/commands/sweep_subscriptions.py`
- Modify: `backend/menu_project/menu/notifications.py`
- Create: `backend/menu_project/menu/tests_sweep.py`

**Interfaces:**
- Consumes: Task 1
- Produces:
  - `manage.py sweep_subscriptions [--dry-run]`
  - `notifications.build_expiring_soon_payload(subscription, days_left) -> dict`
  - `notifications.send_expiring_soon_notification(subscription, days_left)`
  - `notifications.build_subscription_expired_payload(subscription) -> dict` (기존 `build_trial_expired_payload` 를 이름과 문구만 바꾼 것)
  - `notifications.send_subscription_expired_notification(subscription)`

- [ ] **Step 1: 테스트를 쓴다**

`backend/menu_project/menu/tests_sweep.py`:

```python
"""
만료 스윕.

손님 화면이 닫히는 건 이 명령과 무관하다 — is_usable 이 실시간으로 날짜를
본다. 이 명령이 하는 일은 상태를 unpaid 로 내려 목록에서 '끝났다' 고 읽히게
하는 것과, 사장님에게 연락할 수 있도록 우리에게 알리는 것이다.
"""

from datetime import timedelta
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from menu.models import Restaurant


class SweepSubscriptionsTests(TestCase):
    def _store(self, slug, status, days):
        restaurant = Restaurant.objects.create(name=slug, slug=slug)
        subscription = restaurant.subscription
        subscription.status = status
        subscription.current_period_end = (
            timezone.now() + timedelta(days=days) if days is not None else None
        )
        subscription.save()
        return subscription

    def test_a_lapsed_paid_store_becomes_unpaid(self):
        subscription = self._store('lapsed', 'active', -1)
        call_command('sweep_subscriptions')
        subscription.refresh_from_db()
        self.assertEqual(subscription.status, 'unpaid')

    def test_a_running_store_is_left_alone(self):
        subscription = self._store('running', 'active', 10)
        call_command('sweep_subscriptions')
        subscription.refresh_from_db()
        self.assertEqual(subscription.status, 'active')

    def test_partner_is_never_touched(self):
        """파트너는 날짜를 보지 않는다. 옛 날짜가 붙어 있어도 건드리면 안 된다."""
        subscription = self._store('partner-store', 'partner', -400)
        call_command('sweep_subscriptions')
        subscription.refresh_from_db()
        self.assertEqual(subscription.status, 'partner')

    def test_a_never_opened_store_is_not_reported_as_expired(self):
        """
        한 번도 연 적 없는 무료 매장은 만료된 것이 아니다. 여기 섞이면
        가입만 하고 둘러보는 사장님마다 '끝났습니다' 알림이 온다.
        """
        subscription = self._store('free', 'unpaid', None)
        with patch('menu.notifications.send_subscription_expired_notification') as notify:
            call_command('sweep_subscriptions')
        notify.assert_not_called()
        subscription.refresh_from_db()
        self.assertEqual(subscription.status, 'unpaid')

    def test_a_store_about_to_expire_is_warned(self):
        self._store('soon', 'active', 6)
        with patch('menu.notifications.send_expiring_soon_notification') as notify:
            call_command('sweep_subscriptions')
        notify.assert_called_once()

    def test_a_store_with_plenty_of_time_is_not_warned(self):
        self._store('later', 'active', 20)
        with patch('menu.notifications.send_expiring_soon_notification') as notify:
            call_command('sweep_subscriptions')
        notify.assert_not_called()

    def test_dry_run_changes_nothing(self):
        subscription = self._store('lapsed', 'active', -1)
        call_command('sweep_subscriptions', '--dry-run')
        subscription.refresh_from_db()
        self.assertEqual(subscription.status, 'active')
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend/menu_project && ../venv/bin/python manage.py test menu.tests_sweep -v 2`
Expected: FAIL — `CommandError: Unknown command: 'sweep_subscriptions'`

- [ ] **Step 3: 알림 두 개를 쓴다**

`menu/notifications.py` — `build_trial_expired_payload` 를 `build_subscription_expired_payload` 로 이름을 바꾸고 제목·설명을 고친다.

```python
def build_subscription_expired_payload(subscription):
    """이용 기간이 끝난 매장을 Discord 웹훅 JSON 페이로드로 변환한다."""
    restaurant = subscription.restaurant
    email, phone = _owner_contact(restaurant)
    return {
        "embeds": [
            {
                "title": "⏰ 이용 기간 종료 — 손님 화면이 닫혔습니다",
                "description": "연장 안내가 필요합니다. 사장님이 먼저 연락하지 않는 쪽이 보통입니다.",
                "color": 15105570,
                "fields": [
                    {"name": "매장명", "value": restaurant.name or "-", "inline": True},
                    {"name": "주소", "value": f"/{restaurant.slug}", "inline": True},
                    {"name": "이메일", "value": email, "inline": False},
                    {"name": "연락처", "value": phone, "inline": True},
                    {"name": "요금제", "value": subscription.get_plan_display(), "inline": True},
                ],
            }
        ]
    }


def build_expiring_soon_payload(subscription, days_left):
    """곧 끝나는 매장. 끝나고 알리면 이미 손님 화면이 닫힌 뒤다."""
    restaurant = subscription.restaurant
    email, phone = _owner_contact(restaurant)
    return {
        "embeds": [
            {
                "title": f"🔔 이용 기간 {days_left}일 남음",
                "description": "연장 입금을 안내할 시점입니다.",
                "color": 16776960,
                "fields": [
                    {"name": "매장명", "value": restaurant.name or "-", "inline": True},
                    {"name": "주소", "value": f"/{restaurant.slug}", "inline": True},
                    {"name": "이메일", "value": email, "inline": False},
                    {"name": "연락처", "value": phone, "inline": True},
                ],
            }
        ]
    }


def send_subscription_expired_notification(subscription):
    return _send(build_subscription_expired_payload(subscription))


def send_expiring_soon_notification(subscription, days_left):
    return _send(build_expiring_soon_payload(subscription, days_left))
```

`send_trial_expired_notification` 은 지운다.

- [ ] **Step 4: 커맨드를 쓴다**

`backend/menu_project/menu/management/commands/sweep_subscriptions.py`:

```python
"""
이용 기간을 훑어 끝난 것을 내리고, 곧 끝날 것을 알린다.

손님 화면이 닫히는 건 이 명령과 무관하다. is_usable 이 실시간으로 날짜를
보므로 기간은 정확히 만료 시각에 닫힌다. 이 명령이 하는 일은 두 가지다:
상태를 unpaid 로 내려 화면과 목록에서 '끝났다' 고 읽히게 하는 것, 그리고
연장을 안내할 수 있도록 우리에게 알리는 것.

charge_subscriptions 에 얹지 않았다. 그쪽은 첫 줄이 get_provider() 이고
PaymentNotConfigured 를 만나면 통째로 return 한다. 결제 대행사가 없는 지금
거기 섞으면 스윕이 아예 돌지 않는다.

하루 한 번 cron 으로 돈다:
    0 9 * * *  python manage.py sweep_subscriptions
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from menu import notifications
from menu.models import Subscription

# 며칠 전에 알릴지. 입금하고 확인받는 데 걸리는 시간을 감안한다.
WARN_DAYS = 7


class Command(BaseCommand):
    help = '끝난 이용 기간을 미결제로 내리고, 곧 끝날 매장을 알린다'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='상태를 바꾸지 않고 대상만 보여준다')

    def handle(self, *args, **opts):
        now = timezone.now()
        dry_run = opts['dry_run']

        # 상태로 먼저 거른다. 날짜만 보면 옛 결제일을 달고 있는 파트너·해지
        # 매장이 딸려 들어와 영업 중인 가게가 미결제로 떨어진다.
        # 날짜가 없는 구독(=한 번도 연 적 없는 무료 매장)도 여기서 빠진다 —
        # 그건 만료가 아니라 아직 시작하지 않은 것이다.
        lapsed = Subscription.objects.filter(
            status='active',
            current_period_end__lte=now,
        ).select_related('restaurant')

        self.stdout.write(f'만료 {lapsed.count()}건 (기준 {now:%Y-%m-%d %H:%M})')
        for subscription in lapsed:
            label = f'{subscription.restaurant.slug} · {subscription.restaurant.name}'
            if dry_run:
                self.stdout.write(f'  [dry-run] {label}')
                continue
            subscription.status = 'unpaid'
            subscription.save(update_fields=['status', 'updated_at'])
            # 알림이 실패해도 상태는 이미 내려갔다. 반대였다면 웹훅이 죽은
            # 동안 기간이 영원히 이어진다.
            notifications.send_subscription_expired_notification(subscription)
            self.stdout.write(f'  o {label} → 미결제')

        soon = Subscription.objects.filter(
            status='active',
            current_period_end__gt=now,
            current_period_end__lte=now + timedelta(days=WARN_DAYS),
        ).select_related('restaurant')

        self.stdout.write(f'곧 만료 {soon.count()}건')
        for subscription in soon:
            label = f'{subscription.restaurant.slug} · {subscription.restaurant.name}'
            days_left = max(0, (subscription.current_period_end - now).days)
            if dry_run:
                self.stdout.write(f'  [dry-run] {label} ({days_left}일)')
                continue
            notifications.send_expiring_soon_notification(subscription, days_left)
            self.stdout.write(f'  o {label} ({days_left}일 남음)')
```

- [ ] **Step 5: 통과를 확인한다**

Run: `cd backend/menu_project && ../venv/bin/python manage.py test menu.tests_sweep -v 2`
Expected: PASS (7 tests)

- [ ] **Step 6: 남은 참조를 정리한다**

Run: `cd backend/menu_project && grep -rn "trial_expired\|expire_trials" menu/ --include=*.py --include=*.html`
Expected: 결과 없음. 남아 있으면 고친다.

- [ ] **Step 7: 커밋**

```bash
git add backend/menu_project/menu
git commit -m "$(cat <<'EOF'
feat: 기간이 끝나기 전에 알리고 끝나면 내린다

expire_trials 를 sweep_subscriptions 로 갈았다. 체험이 없어졌으므로
만료 대상은 결제한 매장이고, 끝나고 알리면 이미 손님 화면이 닫힌 뒤라
7일 전에 먼저 알린다.

날짜가 없는 구독은 만료가 아니라 아직 시작하지 않은 것이다. 여기 섞이면
가입만 하고 둘러보는 사장님마다 '끝났습니다' 알림이 간다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GgzE1qiTaMD9V6mgF3Tyos
EOF
)"
```

---

### Task 12: 사진 메뉴등록은 무료 1회

**Files:**
- Modify: `backend/menu_project/menu/models.py` (`Subscription.photo_import_count`)
- Create: `backend/menu_project/menu/migrations/0056_subscription_photo_import_count.py`
- Modify: `backend/menu_project/menu/admin_views.py` (`relay_menu_photos`)
- Modify: `backend/menu_project/menu/notifications.py` (`build_menu_photo_payload`)
- Modify: `backend/menu_project/menu/admin.py` (`list_display` 에 되돌림)
- Modify: `backend/menu_project/menu/templates/admin/menu_import.html`
- Create: `backend/menu_project/menu/tests_photo_quota.py`

**Interfaces:**
- Consumes: Task 8, Task 10
- Produces: `Subscription.photo_import_count` (PositiveIntegerField, default 0), `Subscription.photo_import_allowed() -> bool`

- [ ] **Step 1: 테스트를 쓴다**

`backend/menu_project/menu/tests_photo_quota.py`:

```python
"""
사진 메뉴등록은 미결제 매장에 1회.

이 기능의 실체는 비전 API 가 아니라 사람의 손이다. 사진이 Discord 로 오면
우리가 보고 타이핑해 넣는다. 그래서 무제한으로 열어 둘 수 없다.
"""

from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase

from menu.models import Restaurant, UserProfile


class PhotoImportQuotaTests(TestCase):
    def setUp(self):
        self.restaurant = Restaurant.objects.create(name='미결제 바', slug='unpaid-bar')
        self.user = User.objects.create_user('owner@example.com', password='pw-12345678')
        UserProfile.objects.create(user=self.user, restaurant=self.restaurant)
        self.client.force_login(self.user)

    def _send_one_photo(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image
        from io import BytesIO

        buffer = BytesIO()
        Image.new('RGB', (40, 40), 'white').save(buffer, format='JPEG')
        upload = SimpleUploadedFile('menu.jpg', buffer.getvalue(), content_type='image/jpeg')
        return self.client.post(
            '/unpaid-bar/admin/menu/import/', {'menu_image': upload}, follow=True,
        )

    def test_a_free_store_gets_one_send(self):
        with patch('menu.notifications.send_menu_photos', return_value=True):
            self._send_one_photo()

        self.restaurant.subscription.refresh_from_db()
        self.assertEqual(self.restaurant.subscription.photo_import_count, 1)

    def test_a_second_send_is_refused_for_a_free_store(self):
        subscription = self.restaurant.subscription
        subscription.photo_import_count = 1
        subscription.save(update_fields=['photo_import_count'])

        with patch('menu.notifications.send_menu_photos', return_value=True) as send:
            response = self._send_one_photo()

        send.assert_not_called()
        self.assertContains(response, '직접 입력은 계속 무료')

    def test_a_paid_store_is_not_counted(self):
        subscription = self.restaurant.subscription
        subscription.status = 'partner'
        subscription.photo_import_count = 5
        subscription.save(update_fields=['status', 'photo_import_count'])

        with patch('menu.notifications.send_menu_photos', return_value=True) as send:
            self._send_one_photo()

        send.assert_called_once()

    def test_a_failed_send_does_not_spend_the_free_turn(self):
        """
        사진이 못 갔는데 횟수만 줄면 사장님은 한 번도 못 써 보고 끝난다.
        """
        with patch('menu.notifications.send_menu_photos', return_value=False):
            self._send_one_photo()

        self.restaurant.subscription.refresh_from_db()
        self.assertEqual(self.restaurant.subscription.photo_import_count, 0)

    def test_the_alert_says_the_store_has_not_paid(self):
        from menu.notifications import build_menu_photo_payload

        payload = build_menu_photo_payload(self.restaurant, count=3)
        self.assertIn('미결제', str(payload))
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend/menu_project && ../venv/bin/python manage.py test menu.tests_photo_quota -v 2`
Expected: FAIL — `photo_import_count` 속성이 없다

- [ ] **Step 3: 필드와 판정을 더한다**

`menu/models.py` 의 `Subscription` 에 필드를 더한다.

```python
    # 사진으로 메뉴를 올린 횟수. 이 기능의 실체는 비전 API 가 아니라 사람의
    # 손이라 무제한으로 열 수 없다. 매장 평생 누적이고 입금 확인이 되돌리지
    # 않는다 — '무료 1회' 는 맛보기지 매달 주는 몫이 아니다. 다시 열어 줄
    # 일이 생기면 admin 에서 0 으로 내린다.
    photo_import_count = models.PositiveIntegerField(default=0, verbose_name="사진 등록 사용 횟수")

    # 미결제 매장에 주는 무료 횟수.
    FREE_PHOTO_IMPORTS = 1
```

메서드를 더한다.

```python
    def photo_import_allowed(self):
        """
        사진으로 메뉴를 올려도 되는가.

        결제한 매장은 횟수를 아예 보지 않는다. 한 번 결제했다가 기간이
        지난 매장은 카운터가 이미 차 있어 무료 1회가 다시 생기지 않는다.
        """
        if self.is_usable():
            return True
        return self.photo_import_count < self.FREE_PHOTO_IMPORTS
```

- [ ] **Step 4: 마이그레이션**

```bash
cd backend/menu_project && ../venv/bin/python manage.py makemigrations menu --name subscription_photo_import_count
```

- [ ] **Step 5: 중계 뷰를 고친다**

`menu/admin_views.py` 의 `relay_menu_photos` — POST 분기 맨 앞(업로드를 읽기 전)에 넣는다.

```python
    subscription = getattr(restaurant, 'subscription', None)
    page['photo_import_allowed'] = subscription is None or subscription.photo_import_allowed()

    if request.method != 'POST':
        return render(request, template, page)

    if not page['photo_import_allowed']:
        messages.error(
            request,
            '사진으로 등록해 드리는 것은 1회 제공됩니다. 직접 입력은 계속 무료로 쓰실 수 있습니다.',
        )
        return render(request, template, page)
```

전송 성공 뒤, `messages.success` 앞에 카운트를 올린다.

```python
    # 보낸 뒤에 올린다. 못 갔는데 횟수만 줄면 사장님은 한 번도 못 써 보고 끝난다.
    if subscription is not None:
        subscription.photo_import_count += 1
        subscription.save(update_fields=['photo_import_count', 'updated_at'])

    messages.success(
        request,
        f'메뉴판 사진 {len(images)}장을 받았습니다. 확인 후 정리해서 넣어 드리겠습니다. '
        '정리되기 전까지 미리보기는 비어 있습니다 — 그동안 직접 입력으로도 채우실 수 있습니다.',
    )
```

- [ ] **Step 6: 알림에 미결제 표시를 단다**

`menu/notifications.py` 의 `build_menu_photo_payload` 에서 제목을 만들 때 매장 상태를 본다.

```python
def build_menu_photo_payload(restaurant, count, part=None, parts=None):
    subscription = getattr(restaurant, 'subscription', None)
    # 이 사진을 정리하는 데 드는 건 우리 시간이다. 결제 여부가 보여야
    # 무엇부터 할지 고를 수 있다.
    paid = subscription is not None and subscription.is_usable()
    badge = '' if paid else '[미결제] '
```

기존 제목 문자열 앞에 `badge` 를 붙인다.

- [ ] **Step 7: 화면에 안내를 단다**

`menu/templates/admin/menu_import.html` 의 업로드 폼을 감싼다.

```html
{% if not photo_import_allowed %}
<div class="admin-card">
    <h2>사진 등록은 1회 제공됩니다</h2>
    <p>
        보내주신 사진은 사람이 직접 보고 정리해 넣습니다. 그래서 공개 전 매장에는
        한 번만 제공하고 있습니다. <strong>직접 입력은 계속 무료</strong>로 쓰실 수 있고,
        손님 화면을 여시면 사진 등록도 제한 없이 쓰실 수 있습니다.
    </p>
</div>
{% else %}
    ...
{% endif %}
```

`...` 자리에는 **지금 이 템플릿에 있는 업로드 `<form>` 블록을 그대로 옮긴다.** 새로 쓰지 말고 잘라 붙여라 — 그 폼에는 10장 제한 안내, 브라우저 축소 스크립트, 용량 안내가 붙어 있고, 다시 쓰면 그게 조용히 빠진다.

- [ ] **Step 8: admin 에 횟수를 되돌린다**

Task 10 에서 뺐던 `photo_import_count` 를 `SubscriptionAdmin.list_display` 에 다시 넣는다.

- [ ] **Step 9: 통과를 확인한다**

Run: `cd backend/menu_project && ../venv/bin/python manage.py test menu.tests_photo_quota menu.tests_menu_photo_relay -v 2`
Expected: PASS

- [ ] **Step 10: 커밋**

```bash
git add backend/menu_project/menu
git commit -m "$(cat <<'EOF'
feat: 사진으로 메뉴 넣어드리는 건 공개 전 매장에 1회

이 기능의 실체는 비전 API 가 아니라 사람의 손이다. 사진이 오면 우리가
보고 타이핑해 넣는다. 무제한으로 열어 둘 수 없다.

전송에 성공한 뒤에 센다. 못 갔는데 횟수만 줄면 사장님은 한 번도 못 써
보고 끝난다.

그리고 사진을 보낸 직후 미리보기가 비어 있다는 걸 화면이 말하게 했다.
말하지 않으면 빈 메뉴판을 보고 고장인 줄 안다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GgzE1qiTaMD9V6mgF3Tyos
EOF
)"
```

---

### Task 13: 레이아웃 빌더를 감추고, 게이트를 기본으로 켠다

**Files:**
- Modify: `backend/menu_project/menu/admin.py` (`SiteSettingsAdmin.formfield_for_dbfield` 또는 `fieldsets`)
- Modify: `backend/menu_project/menu_project/settings.py`
- Modify: `backend/menu_project/menu/tests_free_tier.py`
- Modify: `README.md` (배포 절차)

**Interfaces:**
- Consumes: 전 태스크
- Produces: `ENFORCE_SUBSCRIPTION` 기본값 `True`. 레이아웃 JSON 두 필드가 admin 폼에 뜨지 않는다.

- [ ] **Step 1: 테스트를 더한다**

`tests_free_tier.py` 에 추가한다.

```python
from django.test import TestCase, override_settings


class TheGateIsOnByDefaultTests(TestCase):
    def test_enforcement_defaults_to_on(self):
        """
        안 켜면 menu_is_live 가 무조건 True 라 전원이 공짜다. 예전에는
        '돈 낼 방법이 없다' 가 이유였지만 이제 계좌이체가 있고, 무료로 쓸
        사람은 미리보기로 산다.
        """
        from django.conf import settings
        self.assertTrue(settings.ENFORCE_SUBSCRIPTION)


class LayoutBuilderIsHiddenTests(TestCase):
    def test_layout_json_fields_are_not_offered_in_admin(self):
        """
        빌더는 저장까지만 되고 손님 화면에 닿지 않는다(별도 스펙에서 고친다).
        그동안 열어 두면 무료 티어의 핵심 화면이 조용히 거짓말을 한다.
        """
        from django.contrib.admin.sites import site as admin_site

        from menu.models import SiteSettings

        model_admin = admin_site._registry[SiteSettings]
        shown = set()
        for _, options in model_admin.fieldsets:
            shown.update(options['fields'])

        self.assertNotIn('category_card_layout_json', shown)
        self.assertNotIn('menu_card_layout_json', shown)
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend/menu_project && ../venv/bin/python manage.py test menu.tests_free_tier -v 2`
Expected: FAIL — 기본값이 False, 레이아웃 필드가 fieldsets 에 있음

- [ ] **Step 3: 기본값을 뒤집는다**

`menu_project/settings.py`:

```python
# 손님 화면을 구독 상태로 잠근다. 기본이 True 인 이유는, 꺼져 있으면
# menu_is_live() 가 무조건 True 를 줘서 전원이 공짜이기 때문이다. 예전에는
# '사장님이 돈 낼 방법도 없이 메뉴판만 꺼진다' 가 기본값을 False 로 둔
# 이유였는데, 계좌이체가 생기면서 전제가 바뀌었다 — 무료로 쓸 사람은
# 미리보기로 산다.
ENFORCE_SUBSCRIPTION = os.environ.get('ENFORCE_SUBSCRIPTION', 'True') == 'True'
```

- [ ] **Step 4: 빌더를 감춘다**

`menu/admin.py` 의 `SiteSettingsAdmin.fieldsets` 에서 `category_card_layout_json` 과 `menu_card_layout_json` 이 들어 있는 섹션을 지우고(또는 두 필드만 빼고) 주석을 남긴다.

```python
        # 레이아웃 빌더는 여기 없다. 저장과 API 전송까지는 되는데 손님 화면이
        # 그 JSON 을 읽지 않아서, 사장님이 배치를 옮기고 저장해도 아무 일도
        # 일어나지 않는다. 연결은 별도 스펙에서 만든다
        # (docs/superpowers/specs/2026-09-12-layout-renderer-design.md).
        # 그때까지 열어 두면 무료 티어의 핵심 화면이 조용히 거짓말을 한다.
```

`formfield_for_dbfield` 의 `LayoutBuilderWidget` 분기는 **그대로 둔다** — 필드를 다시 노출하는 날 위젯이 같이 살아나야 한다.

- [ ] **Step 5: 통과를 확인한다**

Run: `cd backend/menu_project && ../venv/bin/python manage.py test menu -v 1`
Expected: 전부 PASS

- [ ] **Step 6: 배포 절차를 적는다**

`README.md` 에 배포 절차 항목을 더한다.

```markdown
### 계좌이체 게이트 배포 (2026-09)

서버에서 손으로 해야 하는 것:

    # .env
    ENFORCE_SUBSCRIPTION=True      # 기본값이 True 라 생략 가능. 끄면 전원이 공짜다
    CUSTOMER_SITE_URL=https://bar-menu.ddnsfree.com
    BANK_NAME=...
    BANK_ACCOUNT=...
    BANK_HOLDER=...

    # cron — expire_trials 는 삭제됐다
    0 9 * * *  cd ~/bar_menu/backend/menu_project && ../venv/bin/python manage.py sweep_subscriptions

    # 마이그레이션 3개 (0054~0056)
    ../venv/bin/python manage.py migrate

배포 전 확인:

- `DISCORD_WEBHOOK_URL` 이 서버에 살아 있는가 (사진 중계와 입금 알림이 둘 다 이걸 쓴다)
- 파트너 매장(`bid`·`sorok`)이 `partner` 상태 그대로인가
```

- [ ] **Step 7: 커밋**

```bash
git add backend/menu_project README.md
git commit -m "$(cat <<'EOF'
feat: 게이트를 기본으로 켜고 닿지 않는 레이아웃 빌더를 감춘다

안 켜면 menu_is_live 가 무조건 True 라 전원이 공짜다. 예전에는 '돈 낼
방법이 없다' 가 기본값을 False 로 둔 이유였는데, 계좌이체가 생기면서
전제가 바뀌었다.

레이아웃 빌더는 저장과 API 전송까지 되는데 손님 화면이 그 JSON 을 읽지
않는다. 옮기고 저장해도 아무 일도 안 일어나므로, 연결을 만들기 전까지
감춘다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GgzE1qiTaMD9V6mgF3Tyos
EOF
)"
```

---

## 마지막 확인 (모든 태스크 후)

- [ ] `cd backend/menu_project && ../venv/bin/python manage.py test menu -v 1` — 전부 PASS
- [ ] `cd frontend && npx tsc --noEmit && npm run build` — 통과
- [ ] 로컬 수동 확인: 새 계정 가입 → 메뉴 등록 → 미리보기 링크로 메뉴판 + 워터마크 확인 → QR 은 잠금 화면 → 입금 신청 → admin 에서 1개월 확인 → 손님 주소가 토큰 없이 열림 → QR 발행됨
