# 메뉴판 레이아웃 렌더러 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 사장님이 빌더에서 옮긴 카드 배치가 손님 화면에 실제로 그려지게 한다.

**Architecture:** 저장된 `layout_type` 이 `"custom"` 일 때만 절대배치로 그린다. 기본값 매장은 오늘 코드 그대로 돌아, 배포 순간 파트너 매장 화면이 바뀌는 일이 없다. 카드는 빌더 캔버스와 같은 비율의 상자가 되고, 그 안에서 컴포넌트가 %좌표로 놓인다.

**Tech Stack:** Next.js 16 App Router (frontend, JS 테스트 러너 없음 — 프론트 계약은 Django 테스트가 파일을 읽어 대조한다), Django 5.2 (빌더 위젯은 `menu/templates/admin/widgets/layout_builder_widget.html` 의 바닐라 JS)

**Spec:** `docs/superpowers/specs/2026-09-12-layout-renderer-design.md`

## Global Constraints

- 테스트: `cd backend/menu_project && ../venv/bin/python manage.py test menu.<모듈> -v 2`
- 프론트 검사: `cd frontend && npx tsc --noEmit` 와 `NEXT_PUBLIC_APP_URL=x NEXT_PUBLIC_API_URL=x npm run build`
- **파트너 매장(`bid`·`sorok`)의 손님 화면은 한 픽셀도 바뀌면 안 된다.** 그 매장들의 `layout_type` 은 `"default"` 이고, 이 작업이 끝나도 그대로여야 한다.
- **캔버스 비율은 종류마다 다르다.** 카테고리 320×240(4/3), 메뉴 320×440(8/11). `layout_builder_widget.html` 의 `.card-preview-canvas.category-type` / `.menu-type` 높이가 원본이다. 스펙에는 둘 다 4:3 으로 잘못 적혀 있다 — 이 계획의 값이 맞다.
- **저장된 컴포넌트에 없는 id 는 기본값에서 채운다.** 지금 저장된 JSON 에는 `menu_notes`·`cart_button` 이 없다. 없는 것을 '숨김' 으로 읽으면 custom 을 켜는 순간 장바구니 버튼이 사라진다.
- 프론트에 JS 테스트 러너가 없다. 프론트 쪽 계약은 기존 방식대로 **Django 테스트가 파일을 읽어 대조**한다(`menu/tests_free_tier.py` 의 마케팅 문구 대조가 선례다).
- 커밋 메시지는 사용자 관점의 사실 한 줄 + 왜. 기존 어조를 따른다.

---

### Task 1: 레이아웃을 읽는 규칙을 한 곳에 둔다

**Files:**
- Create: `frontend/src/lib/layout.ts`
- Modify: `frontend/src/lib/types.ts`
- Create: `backend/menu_project/menu/tests_layout_contract.py`

**Interfaces:**
- Consumes: 없음
- Produces:
  - `CardKind = 'category' | 'menu'`
  - `CARD_ASPECT: Record<CardKind, string>` — `{category: '4 / 3', menu: '8 / 11'}`
  - `LayoutComponent = {id: string; name: string; visible: boolean; x: number; y: number; w: number; h: number}`
  - `CardLayout = {layout_type: string; components: LayoutComponent[]}`
  - `isCustomLayout(layout: CardLayout | null | undefined): boolean`
  - `resolveComponents(layout, kind): LayoutComponent[]` — 기본값에 저장값을 덮어 돌려준다
  - `boxStyle(component: LayoutComponent): CSSProperties`

- [ ] **Step 1: 프론트·백엔드가 같은 값을 쓰는지 보는 테스트를 쓴다**

`backend/menu_project/menu/tests_layout_contract.py`:

```python
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
WIDGET = Path(__file__).resolve().parent / 'templates' / 'admin' / 'widgets' / 'layout_builder_widget.html'


def _canvas_height(kind):
    """빌더 캔버스 높이(px). .card-preview-canvas.<kind>-type 의 height."""
    css = WIDGET.read_text(encoding='utf-8')
    match = re.search(
        rf'\.card-preview-canvas\.{kind}-type\s*{{[^}}]*height:\s*(\d+)px', css, re.S
    )
    assert match, f'{kind}-type 캔버스 높이를 위젯에서 못 찾았습니다'
    return int(match.group(1))


def _canvas_width():
    css = WIDGET.read_text(encoding='utf-8')
    match = re.search(r'\.card-preview-canvas\s*{{?[^}]*width:\s*(\d+)px', css, re.S)
    assert match, '캔버스 너비를 위젯에서 못 찾았습니다'
    return int(match.group(1))


class AspectRatiosMatchTheBuilderTests(TestCase):
    def _front_aspect(self, kind):
        source = (FRONTEND / 'lib' / 'layout.ts').read_text(encoding='utf-8')
        match = re.search(rf"{kind}:\s*'(\d+)\s*/\s*(\d+)'", source)
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
        block = re.search(rf'{name}\s*=\s*\[(.*?)\]', source, re.S)
        self.assertTrue(block, f'layout.ts 에 {name} 가 없습니다')
        return set(re.findall(r"'([a-z_]+)'", block.group(1)))

    def test_category_ids_match(self):
        backend = {c['id'] for c in default_category_layout()['components']}
        self.assertEqual(self._front_ids('CATEGORY_COMPONENT_IDS'), backend)

    def test_menu_ids_match(self):
        backend = {c['id'] for c in default_menu_layout()['components']}
        self.assertEqual(self._front_ids('MENU_COMPONENT_IDS'), backend)
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend/menu_project && ../venv/bin/python manage.py test menu.tests_layout_contract -v 2`
Expected: FAIL — `frontend/src/lib/layout.ts` 가 없어 `FileNotFoundError`

- [ ] **Step 3: `layout.ts` 를 만든다**

`frontend/src/lib/layout.ts`:

```ts
/**
 * 저장된 카드 레이아웃을 화면에 옮기는 규칙.
 *
 * 값이 빌더(Django 템플릿의 CSS)와 여기 둘로 나뉘어 있다. 갈리면 사장님이
 * 맞춰 놓은 배치가 손님 화면에서 어긋나고, 그 어긋남은 화면에 아무 표시도
 * 남기지 않는다. menu/tests_layout_contract.py 가 두 값을 대조한다.
 */

import type { CSSProperties } from 'react';

export type CardKind = 'category' | 'menu';

/**
 * 카드의 가로세로 비율. 빌더 캔버스와 같아야 WYSIWYG 이 성립한다.
 * 종류마다 다르다 — 카테고리 320×240, 메뉴 320×440.
 */
export const CARD_ASPECT: Record<CardKind, string> = {
  category: '4 / 3',
  menu: '8 / 11',
};

/** 렌더러가 아는 조각들. 기본값(menu/models.py)과 같아야 한다. */
export const CATEGORY_COMPONENT_IDS = ['category_image', 'category_name', 'category_name_en'];
export const MENU_COMPONENT_IDS = [
  'menu_image',
  'menu_name',
  'menu_name_en',
  'menu_price',
  'menu_description',
];

export interface LayoutComponent {
  id: string;
  name: string;
  visible: boolean;
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface CardLayout {
  layout_type: string;
  components: LayoutComponent[];
}

/**
 * 이 매장이 배치를 직접 고쳤는가.
 *
 * 'default' 인 매장은 오늘 코드 그대로 그린다. 이 스위치가 없으면 배포하는
 * 순간 손대지 않은 매장까지 전부 새 배치로 바뀐다.
 */
export function isCustomLayout(layout: CardLayout | null | undefined): boolean {
  return !!layout && layout.layout_type === 'custom' && Array.isArray(layout.components);
}

/**
 * 그릴 조각들. 저장된 값을 기본값 위에 덮는다.
 *
 * 저장된 JSON 에 없는 id 는 기본값의 자리와 visible 을 그대로 쓴다. 지금
 * 저장된 값들에는 나중에 추가되는 조각이 들어 있지 않은데, 없는 것을
 * '숨김' 으로 읽으면 사장님이 켜는 순간 그 조각이 통째로 사라진다.
 */
export function resolveComponents(
  layout: CardLayout,
  defaults: LayoutComponent[],
): LayoutComponent[] {
  const saved = new Map(layout.components.map((c) => [c.id, c]));
  return defaults.map((fallback) => ({ ...fallback, ...(saved.get(fallback.id) ?? {}) }));
}

/** 조각 하나를 카드 안에 놓는 style. 좌표는 카드 크기에 대한 %다. */
export function boxStyle(component: LayoutComponent): CSSProperties {
  return {
    position: 'absolute',
    left: `${component.x}%`,
    top: `${component.y}%`,
    width: `${component.w}%`,
    height: `${component.h}%`,
    overflow: 'hidden',
  };
}
```

- [ ] **Step 4: 타입에 레이아웃을 싣는다**

`frontend/src/lib/types.ts` 의 `SiteSettings` 인터페이스에 더한다.

```ts
  /** 빌더가 저장한 카드 배치. layout_type 이 'custom' 일 때만 쓰인다. */
  category_card_layout_json: CardLayout | null;
  menu_card_layout_json: CardLayout | null;
```

파일 맨 위에 `import type { CardLayout } from './layout';` 를 더한다.

- [ ] **Step 5: 통과를 확인한다**

Run: `cd backend/menu_project && ../venv/bin/python manage.py test menu.tests_layout_contract -v 2`
Expected: PASS (4 tests)

Run: `cd frontend && npx tsc --noEmit`
Expected: 에러 없음

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/lib/layout.ts frontend/src/lib/types.ts backend/menu_project/menu/tests_layout_contract.py
git commit -m "$(cat <<'EOF'
feat: 저장된 카드 배치를 읽는 규칙을 한 곳에 둔다

빌더 캔버스 비율과 조각 id 가 Django 템플릿과 프론트 둘로 나뉜다. 갈리면
사장님이 맞춰 놓은 배치가 손님 화면에서 어긋나는데, 그 어긋남은 화면에
아무 표시도 남기지 않는다. 두 값을 대조하는 테스트를 같이 둔다.

비율은 종류마다 다르다 — 카테고리 4:3, 메뉴 8:11.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GgzE1qiTaMD9V6mgF3Tyos
EOF
)"
```

---

### Task 2: 빌더가 손대면 `layout_type` 을 custom 으로 바꾼다

**Files:**
- Modify: `backend/menu_project/menu/templates/admin/widgets/layout_builder_widget.html`
- Create: `backend/menu_project/menu/tests_layout_builder.py`

**Interfaces:**
- Consumes: Task 1 (`isCustomLayout` 이 보는 값)
- Produces: 빌더가 저장하는 JSON 의 `layout_type` 이 손댄 뒤에는 `"custom"`

- [ ] **Step 1: 위젯이 스위치를 켜는지 보는 테스트를 쓴다**

JS 를 돌릴 수 없으므로 위젯 소스가 그 일을 하는지 읽어서 본다. 약하지만, 이 값이 빠지면 렌더러가 영영 안 도는 자리라 없는 것보다 낫다.

`backend/menu_project/menu/tests_layout_builder.py`:

```python
"""
빌더가 저장하는 JSON 의 모양.

layout_type 이 'custom' 으로 안 바뀌면 렌더러가 영영 안 돈다 — 사장님은
옮기고 저장했는데 손님 화면은 그대로인, 지금과 똑같은 상태가 된다.

위젯은 바닐라 JS 라 여기서 실행할 수 없다. 소스에 그 동작이 있는지만
본다. 실제 동작은 Task 6 의 E2E 가 본다.
"""

from pathlib import Path

from django.test import TestCase

WIDGET = Path(__file__).resolve().parent / 'templates' / 'admin' / 'widgets' / 'layout_builder_widget.html'


class BuilderMarksTheLayoutCustomTests(TestCase):
    def setUp(self):
        self.source = WIDGET.read_text(encoding='utf-8')

    def test_the_widget_writes_custom_when_something_moves(self):
        self.assertIn("layout_type = 'custom'", self.source.replace('"', "'"))

    def test_the_widget_does_not_hardcode_default_on_save(self):
        """
        저장할 때마다 'default' 로 덮어쓰면 스위치가 켜지지 않는다.
        """
        saving = self.source.replace('"', "'")
        self.assertNotIn("layout_type: 'default'", saving)
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend/menu_project && ../venv/bin/python manage.py test menu.tests_layout_builder -v 2`
Expected: FAIL — `layout_type = 'custom'` 이 위젯에 없다

- [ ] **Step 3: 위젯이 스위치를 켜게 한다**

위젯에서 숨은 textarea 에 JSON 을 쓰는 함수를 찾는다.

```bash
cd backend/menu_project && grep -n "JSON.stringify" menu/templates/admin/widgets/layout_builder_widget.html
```

그 함수 안, `JSON.stringify` 직전에 넣는다.

```javascript
            // 사장님이 실제로 손댔다는 표시. 이게 없으면 손님 화면 렌더러가
            // 영영 안 돈다 — 옮기고 저장했는데 그대로인 지금 상태가 된다.
            // menu/api 는 이 값만 보고 갈래를 탄다.
            data.layout_type = 'custom';
```

`data` 가 그 함수에서 쓰는 객체 이름이 아니면 실제 이름으로 바꾼다.

- [ ] **Step 4: 통과를 확인한다**

Run: `cd backend/menu_project && ../venv/bin/python manage.py test menu.tests_layout_builder -v 2`
Expected: PASS (2 tests)

- [ ] **Step 5: 커밋**

```bash
git add backend/menu_project/menu
git commit -m "$(cat <<'EOF'
feat: 빌더에서 배치를 고치면 custom 으로 표시한다

이 표시가 없으면 손님 화면 렌더러가 영영 안 돈다. 손대지 않은 매장은
default 로 남아 오늘 코드 그대로 그려진다 — 배포하는 순간 파트너 매장
화면이 바뀌는 것을 막는 유일한 장치다.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GgzE1qiTaMD9V6mgF3Tyos
EOF
)"
```

---

### Task 3: 카테고리 카드를 배치대로 그린다

**Files:**
- Create: `frontend/src/components/CategoryCard.tsx`
- Modify: `frontend/src/app/[restaurantSlug]/page.tsx`
- Modify: `frontend/src/styles/globals.css`
- Modify: `backend/menu_project/menu/tests_layout_contract.py`

**Interfaces:**
- Consumes: Task 1 (`CARD_ASPECT`, `isCustomLayout`, `resolveComponents`, `boxStyle`)
- Produces: `<CategoryCard category={...} href={...} layout={...} />`

카테고리 조각 셋은 이렇게 그린다.

| id | 그리는 것 |
|---|---|
| `category_image` | `category.category_image` (없으면 아무것도 안 그린다) |
| `category_name` | `category.name` · 클래스 `category-name-ko` |
| `category_name_en` | `category.name_en` · 클래스 `category-name-en` |

클래스는 그대로 쓴다. 폰트·색·크기는 `styles.ts` 가 CSS 변수로 이미 주입하고 있어서, 클래스를 바꾸면 사장님이 맞춰 둔 글꼴이 통째로 날아간다.

- [ ] **Step 1: 카드가 배치를 따르는지 보는 테스트를 쓴다**

`tests_layout_contract.py` 에 추가한다.

```python
class CategoryCardHonorsTheLayoutTests(TestCase):
    """
    프론트에 JS 테스트 러너가 없다. 렌더러가 규칙을 실제로 쓰는지 소스로
    확인하고, 그려진 결과는 Task 6 의 E2E 가 본다.
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
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend/menu_project && ../venv/bin/python manage.py test menu.tests_layout_contract -v 2`
Expected: FAIL — `CategoryCard.tsx` 가 없어 `FileNotFoundError`

- [ ] **Step 3: 카드 컴포넌트를 만든다**

`frontend/src/components/CategoryCard.tsx`:

```tsx
import Link from 'next/link';

import {
  CARD_ASPECT,
  boxStyle,
  isCustomLayout,
  resolveComponents,
  type CardLayout,
  type LayoutComponent,
} from '@/lib/layout';
import type { Category } from '@/lib/types';

/**
 * 손님이 보는 카테고리 카드.
 *
 * 사장님이 빌더에서 배치를 고친 매장(layout_type === 'custom')만 절대배치로
 * 그린다. 손대지 않은 매장은 예전 마크업 그대로다 — 이 갈래가 없으면
 * 배포하는 순간 손대지 않은 매장까지 전부 새 배치로 바뀐다.
 */

/** 빌더 기본값과 같은 자리. 저장된 JSON 에 빠진 조각을 여기서 채운다. */
const DEFAULTS: LayoutComponent[] = [
  { id: 'category_image', name: '카테고리 이미지', visible: true, x: 0, y: 0, w: 100, h: 65 },
  { id: 'category_name', name: '카테고리명 (한글)', visible: true, x: 5, y: 70, w: 90, h: 15 },
  { id: 'category_name_en', name: '카테고리명 (영문)', visible: true, x: 5, y: 85, w: 90, h: 10 },
];

function Piece({ component, category }: { component: LayoutComponent; category: Category }) {
  if (!component.visible) return null;

  if (component.id === 'category_image') {
    if (!category.category_image) return null;
    return (
      <div style={boxStyle(component)}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={category.category_image}
          alt=""
          loading="lazy"
          style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
        />
      </div>
    );
  }

  if (component.id === 'category_name') {
    return (
      <div style={boxStyle(component)}>
        <h3 className="category-name-ko layout-text">{category.name}</h3>
      </div>
    );
  }

  if (component.id === 'category_name_en') {
    if (!category.name_en) return null;
    return (
      <div style={boxStyle(component)}>
        <p className="category-name-en layout-text">{category.name_en}</p>
      </div>
    );
  }

  return null;
}

export default function CategoryCard({
  category,
  href,
  layout,
}: {
  category: Category;
  href: string;
  layout: CardLayout | null | undefined;
}) {
  if (!isCustomLayout(layout)) {
    return (
      <Link href={href} className="category-card">
        {category.name_en && <p className="category-name-en">{category.name_en}</p>}
        <h3 className="category-name-ko">{category.name}</h3>
      </Link>
    );
  }

  return (
    <Link
      href={href}
      className="category-card category-card-custom"
      style={{ aspectRatio: CARD_ASPECT.category }}
    >
      {resolveComponents(layout as CardLayout, DEFAULTS).map((component) => (
        <Piece key={component.id} component={component} category={category} />
      ))}
    </Link>
  );
}
```

- [ ] **Step 4: 절대배치가 설 자리를 CSS 에 만든다**

`frontend/src/styles/globals.css` 끝에 더한다.

```css
/* ─────────────────────────────────────────────────────────────
   빌더로 배치를 고친 매장의 카드.

   .category-card 의 padding 과 text-align 은 예전 흐름 배치용이라
   절대배치에서는 좌표를 밀어낸다. custom 일 때만 걷어낸다.

   글자는 상자 밖으로 넘치면 안 된다. 상자 높이는 사장님이 정한 값이고,
   넘친 글자는 아래 조각을 덮는다.
   ───────────────────────────────────────────────────────────── */
.category-card-custom,
.menu-item-custom {
  position: relative;
  padding: 0;
  text-align: left;
  overflow: hidden;
  display: block;
}

.layout-text {
  margin: 0;
  width: 100%;
  height: 100%;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
  line-clamp: 3;
  overflow: hidden;
  text-overflow: ellipsis;
  word-break: keep-all;
}
```

- [ ] **Step 5: 목록이 그 카드를 쓰게 한다**

`frontend/src/app/[restaurantSlug]/page.tsx` 의 `categories.map(...)` 블록을 바꾼다.

```tsx
              {categories.map((category) => (
                <CategoryCard
                  key={category.id}
                  category={category}
                  href={`/${restaurantSlug}/category/${category.id}`}
                  layout={settings?.category_card_layout_json}
                />
              ))}
```

파일 상단에 `import CategoryCard from '@/components/CategoryCard';` 를 더하고, 쓰지 않게 된 `Link` import 가 남으면 정리한다.

- [ ] **Step 6: 통과를 확인한다**

Run: `cd backend/menu_project && ../venv/bin/python manage.py test menu.tests_layout_contract -v 2`
Expected: PASS

Run: `cd frontend && npx tsc --noEmit && NEXT_PUBLIC_APP_URL=x NEXT_PUBLIC_API_URL=x npm run build`
Expected: 통과

- [ ] **Step 7: 손대지 않은 매장이 그대로인지 눈으로 본다**

```bash
# 터미널 1
cd backend/menu_project && ../venv/bin/python manage.py runserver 8010
# 터미널 2 — .env.local 이 운영을 가리키므로 반드시 덮어쓴다
cd frontend && NEXT_PUBLIC_API_URL=http://localhost:8010 npm run dev
```

`http://localhost:3000/bid` 를 연다. `bid` 는 `layout_type: "default"` 이므로 **오늘과 똑같이** 보여야 한다. 조금이라도 다르면 갈래가 잘못 탄 것이다.

- [ ] **Step 8: 커밋**

```bash
git add frontend/src backend/menu_project/menu
git commit -m "$(cat <<'EOF'
feat: 사장님이 옮긴 카테고리 배치를 손님 화면에 그린다

layout_type 이 custom 인 매장만 절대배치로 그린다. 손대지 않은 매장은
예전 마크업 그대로다.

저장된 JSON 에 없는 조각은 기본값에서 채운다. 없는 것을 '숨김' 으로
읽으면 나중에 조각이 늘 때 사장님 화면에서 통째로 사라진다.

클래스 이름은 그대로 뒀다. 폰트·색·크기를 styles.ts 가 그 클래스에 CSS
변수로 주입하고 있어서, 갈면 사장님이 맞춰 둔 글꼴이 날아간다.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GgzE1qiTaMD9V6mgF3Tyos
EOF
)"
```

---

### Task 4: 빌더에 장바구니와 노트를 더한다

**Files:**
- Modify: `backend/menu_project/menu/models.py` (`default_menu_layout`)
- Create: `backend/menu_project/menu/migrations/0057_menu_layout_adds_notes_and_cart.py`
- Modify: `frontend/src/lib/layout.ts` (`MENU_COMPONENT_IDS`)
- Modify: `backend/menu_project/menu/tests_layout_contract.py`

**Interfaces:**
- Consumes: Task 1
- Produces: `default_menu_layout()` 의 컴포넌트가 7개 — 기존 5개 + `menu_notes` + `cart_button`

메뉴 카드가 custom 이면 `display_mode` 를 무시하고 빌더가 배치를 전부 정한다(스펙의 결정). 그런데 지금 빌더는 `notes` 와 장바구니 버튼을 모른다. 그대로 전권을 주면 **custom 을 켜는 순간 장바구니가 사라진다.** 렌더러보다 먼저 이걸 메운다.

- [ ] **Step 1: 테스트를 더한다**

`tests_layout_contract.py` 에 추가한다.

```python
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
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend/menu_project && ../venv/bin/python manage.py test menu.tests_layout_contract -v 2`
Expected: FAIL — `cart_button` 과 `menu_notes` 가 없다

- [ ] **Step 3: 기본값을 넓힌다**

`menu/models.py` 의 `default_menu_layout` 을 바꾼다. 기존 다섯 조각의 자리는 건드리지 않고, 설명(89~99)을 줄여 두 조각을 넣는다.

```python
def default_menu_layout():
    return {
        "layout_type": "default",
        "components": [
            {"id": "menu_image", "name": "메뉴 이미지", "visible": True, "x": 0, "y": 0, "w": 100, "h": 50},
            {"id": "menu_name", "name": "메뉴명 (한글)", "visible": True, "x": 5, "y": 55, "w": 90, "h": 12},
            {"id": "menu_name_en", "name": "메뉴명 (영문)", "visible": True, "x": 5, "y": 68, "w": 90, "h": 8},
            {"id": "menu_price", "name": "가격", "visible": True, "x": 5, "y": 78, "w": 60, "h": 10},
            # 장바구니 버튼과 노트는 빌더가 모르던 조각이다. custom 이 켜지면
            # 빌더가 배치를 전부 정하므로, 여기 없으면 그 순간 화면에서 사라진다.
            {"id": "cart_button", "name": "장바구니 버튼", "visible": True, "x": 70, "y": 78, "w": 25, "h": 10},
            {"id": "menu_description", "name": "메뉴 설명", "visible": True, "x": 5, "y": 89, "w": 90, "h": 6},
            {"id": "menu_notes", "name": "메뉴 노트", "visible": True, "x": 5, "y": 95, "w": 90, "h": 5},
        ]
    }
```

- [ ] **Step 4: 프론트 상수를 맞춘다**

`frontend/src/lib/layout.ts` 의 `MENU_COMPONENT_IDS` 에 `'cart_button'` 과 `'menu_notes'` 를 더한다.

- [ ] **Step 5: 마이그레이션을 만든다**

```bash
cd backend/menu_project && ../venv/bin/python manage.py makemigrations menu --name menu_layout_adds_notes_and_cart
```

기본값 callable 이 바뀌면 Django 가 `AlterField` 를 만든다. **기존 행은 안 바뀐다** — 그건 의도다. 이미 저장된 JSON 에 두 조각이 없어도 Task 1 의 `resolveComponents` 가 기본값에서 채운다. 마이그레이션 파일 맨 위에 그 사실을 주석으로 적는다.

```python
# 기존 행의 JSON 은 건드리지 않는다. 빠진 조각은 화면 쪽
# resolveComponents 가 기본값에서 채운다 — 저장된 값을 일괄로 고치면
# 사장님이 숨겨 둔 조각까지 되살아난다.
```

- [ ] **Step 6: 통과를 확인한다**

Run: `cd backend/menu_project && ../venv/bin/python manage.py test menu -v 1`
Expected: PASS 전부

- [ ] **Step 7: 커밋**

```bash
git add backend/menu_project/menu frontend/src/lib/layout.ts
git commit -m "$(cat <<'EOF'
feat: 빌더가 장바구니 버튼과 노트도 알게 한다

custom 레이아웃이면 display_mode 를 무시하고 빌더가 배치를 전부 정한다.
그런데 빌더는 이 둘을 몰랐다 — 그대로 전권을 주면 사장님이 custom 을
켜는 순간 장바구니 버튼이 사라진다.

기존 행의 JSON 은 안 고친다. 빠진 조각은 화면 쪽에서 기본값으로 채운다
— 일괄로 고치면 사장님이 숨겨 둔 조각까지 되살아난다.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GgzE1qiTaMD9V6mgF3Tyos
EOF
)"
```

---

### Task 5: 메뉴 카드를 배치대로 그린다

**Files:**
- Create: `frontend/src/components/MenuCardLayout.tsx`
- Modify: `frontend/src/components/MenuCard.tsx`
- Modify: `backend/menu_project/menu/tests_layout_contract.py`

**Interfaces:**
- Consumes: Task 1, Task 4
- Produces: `<MenuCardLayout item={...} layout={...} enableCart={...} onImageClick={...} />`

`MenuCard.tsx` 는 이미 네 갈래(`auto`/`image_only`/`text_only`/`combined`)로 257줄이다. 거기에 다섯 번째 갈래를 끼우면 읽을 수 없어진다. custom 갈래는 **별도 파일**로 빼고 `MenuCard` 는 맨 앞에서 한 번만 갈라진다.

라이트박스·상세보기는 배치가 아니라 성질이라 그대로 따라간다 — 이미지 조각에 라이트박스, 카드 전체에 상세보기.

- [ ] **Step 1: 테스트를 더한다**

```python
class MenuCardHonorsTheLayoutTests(TestCase):
    def setUp(self):
        self.layout_source = (FRONTEND / 'components' / 'MenuCardLayout.tsx').read_text(encoding='utf-8')
        self.card_source = (FRONTEND / 'components' / 'MenuCard.tsx').read_text(encoding='utf-8')

    def test_the_custom_branch_lives_in_its_own_file(self):
        """MenuCard 는 이미 네 갈래로 257줄이다. 다섯 번째를 끼우면 못 읽는다."""
        self.assertIn('MenuCardLayout', self.card_source)

    def test_it_branches_on_the_layout_type(self):
        self.assertIn('isCustomLayout', self.card_source)

    def test_it_draws_the_cart_button(self):
        self.assertIn('cart_button', self.layout_source)

    def test_it_draws_the_notes(self):
        self.assertIn('menu_notes', self.layout_source)

    def test_it_keeps_the_class_names_that_carry_the_owner_fonts(self):
        for klass in ('menu-name-ko', 'menu-name-en', 'menu-price', 'menu-description', 'menu-notes'):
            self.assertIn(klass, self.layout_source)

    def test_adding_to_the_cart_still_goes_through_the_same_event(self):
        """
        Cart.tsx 가 window 의 add-to-cart 를 듣는다. 다른 길을 만들면
        custom 매장만 장바구니가 조용히 안 담긴다.
        """
        self.assertIn('add-to-cart', self.layout_source)
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend/menu_project && ../venv/bin/python manage.py test menu.tests_layout_contract -v 2`
Expected: FAIL — `MenuCardLayout.tsx` 가 없다

- [ ] **Step 3: custom 갈래를 만든다**

`frontend/src/components/MenuCardLayout.tsx`:

```tsx
'use client';

import {
  CARD_ASPECT,
  boxStyle,
  resolveComponents,
  type CardLayout,
  type LayoutComponent,
} from '@/lib/layout';
import type { MenuItem } from '@/lib/types';
import Nl2br from './Nl2br';

/**
 * 사장님이 빌더에서 배치를 고친 매장의 메뉴 카드.
 *
 * MenuCard 는 이미 display_mode 로 네 갈래를 그린다. 거기에 다섯 번째를
 * 끼우면 읽을 수 없어져서 갈래를 통째로 여기로 뺐다.
 *
 * custom 이면 display_mode 를 보지 않는다. 주인이 둘이면 '이미지를 보이게
 * 놓았는데 안 나온다' 가 생기고, 그걸 설명할 자리가 화면에 없다.
 */

const DEFAULTS: LayoutComponent[] = [
  { id: 'menu_image', name: '메뉴 이미지', visible: true, x: 0, y: 0, w: 100, h: 50 },
  { id: 'menu_name', name: '메뉴명 (한글)', visible: true, x: 5, y: 55, w: 90, h: 12 },
  { id: 'menu_name_en', name: '메뉴명 (영문)', visible: true, x: 5, y: 68, w: 90, h: 8 },
  { id: 'menu_price', name: '가격', visible: true, x: 5, y: 78, w: 60, h: 10 },
  { id: 'cart_button', name: '장바구니 버튼', visible: true, x: 70, y: 78, w: 25, h: 10 },
  { id: 'menu_description', name: '메뉴 설명', visible: true, x: 5, y: 89, w: 90, h: 6 },
  { id: 'menu_notes', name: '메뉴 노트', visible: true, x: 5, y: 95, w: 90, h: 5 },
];

function Piece({
  component,
  item,
  enableCart,
  onImageClick,
}: {
  component: LayoutComponent;
  item: MenuItem;
  enableCart: boolean;
  onImageClick: (e: React.MouseEvent) => void;
}) {
  if (!component.visible) return null;
  const style = boxStyle(component);

  switch (component.id) {
    case 'menu_image':
      if (!item.menu_image) return null;
      return (
        <div style={style} data-expand={item.click_expand || undefined} onClick={onImageClick}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={item.menu_image}
            alt={item.name}
            loading="lazy"
            style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
          />
        </div>
      );

    case 'menu_name':
      return (
        <div style={style}>
          <span className="menu-name-ko layout-text"><Nl2br text={item.name} /></span>
        </div>
      );

    case 'menu_name_en':
      if (!item.name_en) return null;
      return (
        <div style={style}>
          <span className="menu-name-en layout-text"><Nl2br text={item.name_en} /></span>
        </div>
      );

    case 'menu_price':
      return (
        <div style={style}>
          <div className="menu-price layout-text"><Nl2br text={item.price} /></div>
        </div>
      );

    case 'menu_description':
      if (!item.description) return null;
      return (
        <div style={style}>
          <div className="menu-description layout-text"><Nl2br text={item.description} /></div>
        </div>
      );

    case 'menu_notes':
      if (!item.notes) return null;
      return (
        <div style={style}>
          <span className="menu-notes layout-text"><Nl2br text={item.notes} /></span>
        </div>
      );

    case 'cart_button':
      if (!enableCart) return null;
      return (
        <div style={style}>
          <button
            className="add-cart-btn"
            style={{ width: '100%', height: '100%' }}
            onClick={(e) => {
              e.stopPropagation();
              // Cart.tsx 가 듣는 창구다. 다른 길을 만들면 custom 매장만
              // 장바구니가 조용히 안 담긴다.
              window.dispatchEvent(new CustomEvent('add-to-cart', { detail: item }));
            }}
          >
            +
          </button>
        </div>
      );

    default:
      return null;
  }
}

export default function MenuCardLayout({
  item,
  layout,
  enableCart,
  onImageClick,
}: {
  item: MenuItem;
  layout: CardLayout;
  enableCart: boolean;
  onImageClick: (e: React.MouseEvent) => void;
}) {
  return (
    <div
      className="menu-item menu-item-custom"
      id={`menu-${item.id}`}
      style={{ aspectRatio: CARD_ASPECT.menu }}
    >
      {resolveComponents(layout, DEFAULTS).map((component) => (
        <Piece
          key={component.id}
          component={component}
          item={item}
          enableCart={enableCart}
          onImageClick={onImageClick}
        />
      ))}
    </div>
  );
}
```

`Nl2br` 이 별도 파일이 아니면 `MenuCard.tsx` 에서 export 하고 여기서 import 한다.

- [ ] **Step 4: MenuCard 가 맨 앞에서 갈라지게 한다**

`MenuCard.tsx` 의 `return (` 직전에 넣는다. `layout` 은 `MenuCard` 의 새 prop 이고, 부르는 쪽(카테고리 페이지)이 `settings?.menu_card_layout_json` 을 넘긴다.

```tsx
  // custom 이면 display_mode 를 보지 않는다. 주인이 둘이면 '이미지를 보이게
  // 놓았는데 안 나온다' 가 생기고, 그걸 설명할 자리가 화면에 없다.
  if (isCustomLayout(layout)) {
    return (
      <>
        <div onClick={handleItemClick} data-detail={item.enable_detail_view ? 'true' : undefined}>
          <MenuCardLayout
            item={item}
            layout={layout as CardLayout}
            enableCart={enableCart}
            onImageClick={handleExpandClick}
          />
        </div>
        {lightboxOpen && item.menu_image && (
          <Lightbox
            src={item.menu_image}
            alt={item.name}
            style={item.lightbox_style}
            opacity={item.lightbox_opacity}
            onClose={() => setLightboxOpen(false)}
          />
        )}
        {detailOpen && (
          <DetailModal item={item} opacity={item.lightbox_opacity} onClose={() => setDetailOpen(false)} />
        )}
      </>
    );
  }
```

`MenuCard` 를 부르는 곳(`app/[restaurantSlug]/category/[categoryId]/page.tsx`)에 `layout={settings?.menu_card_layout_json}` 를 넘긴다.

- [ ] **Step 5: 통과를 확인한다**

Run: `cd backend/menu_project && ../venv/bin/python manage.py test menu -v 1`
Expected: PASS

Run: `cd frontend && npx tsc --noEmit && NEXT_PUBLIC_APP_URL=x NEXT_PUBLIC_API_URL=x npm run build`
Expected: 통과

- [ ] **Step 6: 커밋**

```bash
git add frontend/src backend/menu_project/menu
git commit -m "$(cat <<'EOF'
feat: 사장님이 옮긴 메뉴 배치를 손님 화면에 그린다

custom 이면 display_mode 를 보지 않는다. 주인이 둘이면 '이미지를 보이게
놓았는데 안 나온다' 가 생기고, 그걸 설명할 자리가 화면에 없다.

갈래를 별도 파일로 뺐다. MenuCard 는 이미 네 갈래로 257줄이라 다섯 번째를
끼우면 못 읽는다.

장바구니는 기존 add-to-cart 이벤트를 그대로 쓴다. 다른 길을 만들면 custom
매장만 조용히 안 담긴다.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GgzE1qiTaMD9V6mgF3Tyos
EOF
)"
```

---

### Task 6: 빌더를 고치고 문을 연다

**Files:**
- Modify: `backend/menu_project/menu/templates/admin/widgets/layout_builder_widget.html`
- Modify: `backend/menu_project/menu/admin.py`
- Modify: `backend/menu_project/menu/tests_free_tier.py`

**Interfaces:**
- Consumes: Task 1~5 전부
- Produces: Django admin 사이트 설정에 레이아웃 두 필드가 다시 보인다

2026-09-12 에 손으로 확인한 결함 둘을 함께 고친다. 포갠 상자를 다시 못 고르는 것과, mousedown 후 1px 만 움직여도 드래그가 되는 것이다.

- [ ] **Step 1: 감춰둔 것을 도로 여는 테스트로 바꾼다**

`tests_free_tier.py` 의 `LayoutBuilderIsHiddenTests` 를 지우고 이것으로 갈아넣는다.

```python
class LayoutBuilderIsAvailableTests(TestCase):
    """
    2026-09-12 에 감췄던 것을 되돌린다. 그때는 저장만 되고 손님 화면에
    닿지 않아서 조용히 거짓말을 했는데, 이제 닿는다.
    """

    def test_layout_fields_are_offered_in_admin(self):
        from django.contrib.admin.sites import site

        from menu.models import SiteSettings

        model_admin = site._registry[SiteSettings]
        shown = set()
        for _, options in model_admin.fieldsets:
            shown.update(options['fields'])

        self.assertIn('category_card_layout_json', shown)
        self.assertIn('menu_card_layout_json', shown)
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend/menu_project && ../venv/bin/python manage.py test menu.tests_free_tier -v 2`
Expected: FAIL — 두 필드가 fieldsets 에 없다

- [ ] **Step 3: 빌더의 결함 둘을 고친다**

`layout_builder_widget.html` 에서 상자를 고르는 곳과 드래그를 시작하는 곳을 찾는다.

```bash
cd backend/menu_project && grep -n "mousedown\|selectBox\|selected" menu/templates/admin/widgets/layout_builder_widget.html | head -20
```

**(가) 드래그 임계값.** mousedown 위치를 기억해 두고, 4px 넘게 움직인 뒤에야 드래그로 친다.

```javascript
        // 임계값이 없으면 '고르려던 클릭' 이 늘 '옮김' 이 된다. 상자를
        // 누르기만 해도 좌표가 바뀌어서, 고를 때마다 배치가 조금씩 흐트러진다.
        const DRAG_THRESHOLD_PX = 4;
```

mousedown 에서 `startX`/`startY` 를 저장하고, mousemove 에서 이동 거리가 임계값을 넘을 때만 `dragging = true` 로 바꾼 뒤 좌표를 고친다.

**(나) 포갠 상자 고르기.** 같은 자리를 다시 누르면 그 자리에 겹친 상자들을 돌아가며 고른다.

```javascript
        // 상자를 정확히 포개 놓으면 위 상자가 z-index 10 으로 덮어서 아래
        // 것을 다시 고를 수 없었다. 같은 자리를 다시 누르면 겹친 것들을
        // 돌아가며 고른다.
        function boxesAt(clientX, clientY) {
            return Array.from(canvas.querySelectorAll('.comp-box')).filter(function (box) {
                const r = box.getBoundingClientRect();
                return clientX >= r.left && clientX <= r.right && clientY >= r.top && clientY <= r.bottom;
            });
        }
```

mousedown 에서 `boxesAt(...)` 을 부르고, 지금 고른 상자가 그 목록에 있으면 **다음** 것을, 없으면 첫 번째를 고른다.

- [ ] **Step 4: 문을 연다**

`menu/admin.py` 의 `SiteSettingsAdmin.fieldsets` 맨 앞에 되돌린다. 2026-09-12 에 남긴 "여기 없다" 주석은 지운다.

```python
    fieldsets = (
        ('카드 레이아웃 커스터마이징 설정', {
            'fields': ('category_card_layout_json', 'menu_card_layout_json'),
            'description': '여기서 옮긴 배치는 저장하면 손님 화면에 그대로 반영됩니다.',
        }),
        ('기본 설정', {
```

- [ ] **Step 5: 통과를 확인한다**

Run: `cd backend/menu_project && ../venv/bin/python manage.py test menu -v 1`
Expected: PASS 전부

- [ ] **Step 6: 브라우저로 전 구간을 확인한다**

서버 둘을 띄운다.

```bash
cd backend/menu_project && ../venv/bin/python manage.py runserver 8010
cd frontend && NEXT_PUBLIC_API_URL=http://localhost:8010 npm run dev
```

`demo-izakaya` 로 확인한다. **`bid`·`sorok` 은 쓰지 않는다** — 파트너 매장이다.

1. `http://localhost:3000/demo-izakaya` 를 열어 지금 모습을 기억한다(아직 default)
2. `http://localhost:8010/admin/menu/sitesettings/` 에서 그 매장 설정을 연다
3. 카테고리 빌더에서 영문명을 "화면에 표시" 해제하고 저장한다
4. 손님 화면을 새로고침한다 — **영문명이 사라져야 한다**
5. 한글명 상자를 영문명 위에 정확히 포개고, 같은 자리를 두 번 눌러 **아래 상자가 골라지는지** 본다
6. 상자를 누르기만 하고 놓는다 — 좌표가 **안 바뀌어야** 한다
7. `http://localhost:3000/bid` 를 연다 — **1번에서 본 것과 똑같아야 한다**

4번이 이 작업의 전부다. 지금까지는 저기서 아무 일도 일어나지 않았다.

- [ ] **Step 7: 커밋**

```bash
git add backend/menu_project/menu
git commit -m "$(cat <<'EOF'
feat: 레이아웃 빌더를 다시 연다

2026-09-12 에 감췄던 것을 되돌린다. 그때는 저장만 되고 손님 화면에 닿지
않아서 조용히 거짓말을 했는데, 이제 닿는다.

같이 고친 것 둘. 상자를 정확히 포개면 위 상자가 덮어서 아래 것을 다시
고를 수 없었다. 그리고 mousedown 후 1px 만 움직여도 드래그로 처리돼,
고르려던 클릭이 늘 배치를 조금씩 흐트러뜨렸다.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GgzE1qiTaMD9V6mgF3Tyos
EOF
)"
```

---

## 마지막 확인 (모든 태스크 후)

- [ ] `cd backend/menu_project && ../venv/bin/python manage.py test menu -v 1` — 전부 PASS
- [ ] `cd frontend && npx tsc --noEmit && NEXT_PUBLIC_APP_URL=x NEXT_PUBLIC_API_URL=x npm run build` — 통과
- [ ] **`bid` 손님 화면이 작업 전과 똑같다** — 이 작업에서 가장 위험한 지점이다. 다르면 `layout_type` 갈래가 잘못 탄 것이므로 멈춘다
- [ ] develop 배포 후 `https://develop.bar-menu.ddnsfree.com/bid` 도 같은지 본다
