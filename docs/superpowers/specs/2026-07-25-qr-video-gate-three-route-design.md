# QR 진입 전용 비디오 게이트 (3주소 분리) — 설계

- 날짜: 2026-07-25
- 브랜치: develop
- 상태: 승인됨

## 배경 / 목표

인트로/로딩 비디오를 **QR로 접속한 손님에게만** 보여주고, 메뉴 링크로 직접 들어온 손님(이미 와이파이 인증돼 창이 켜진 사람)에게는 **재인증 없이 비디오도 건너뛰고** 바로 메뉴를 보여준다. 친구가 준 UX 플로우차트(기능1/기능2)의 골자.

핵심 아이디어: 비디오 노출을 **라우트 분리**로 제어한다. IP 인증은 이미 `layout.tsx`가 `/{slug}/*` 전체에 적용하므로 그대로 재활용한다.

## 3주소 구조

| 주소 | 경로 | 역할 |
|---|---|---|
| **주소A** | `/{slug}/enter` (신규) | QR 진입점. IP 통과 시 비디오 재생 → `/{slug}`로 리디렉션. QR이 여기를 가리킴. |
| **주소B** | `/{slug}` (+ `/category/{id}`) | 메뉴판. 링크 직접 진입. 비디오 없음. |
| **주소C** | (라우트 아님) `WifiRestrictionBlock` | IP 불일치 시 layout이 렌더하는 잠금화면. |

IP 게이트(`layout.tsx`)는 주소A·주소B 모두에 그대로 적용된다. 불일치면 주소C가 대신 렌더된다.

## 변경 사항

### 1. 주소A — 신규 라우트 `frontend/src/app/[restaurantSlug]/enter/page.tsx`
- `'use client'` 컴포넌트. `useRestaurant()`로 `intro_video`/`loading_video_2` 획득.
- 재생 순서: `intro_video`(1차) → `loading_video_2`(2차, 탭하면 스킵) → 끝나면 `router.replace('/{slug}')`.
- **매 진입마다 재생**(쿨다운 없음). 둘 다 없으면 즉시 `/{slug}`로 리디렉션.
- 자동재생 실패(모바일 정책) 대비: 각 단계에서 6초 내 `playing` 이벤트가 안 오면 다음 단계로 advance(재생 중인 영상은 자르지 않음 — 기존 IntroManager의 5초 무조건 컷 문제를 피함).
- 풀스크린 검정 오버레이(`position:fixed; inset:0; background:#000`).

### 2. 주소B — `frontend/src/app/[restaurantSlug]/page.tsx` + `IntroManager.tsx`
- `IntroManager`에 `autoPlayIntro?: boolean`(기본 true) prop 추가. 자동재생 useEffect를 `if (!autoPlayIntro) return;`로 가드.
- `page.tsx`에서 `<IntroManager autoPlayIntro={false} .../>`로 호출 → 메뉴 진입 시 인트로 자동재생 안 함.
- **수동 "메뉴판 설명서" 카드(`show_manual_card`)는 그대로 유지**(회귀 방지). IntroManager는 계속 렌더하되 자동재생만 끔.

### 3. 주소C — `frontend/src/components/WifiRestrictionBlock.tsx` 재디자인
- 디자인 이미지(`bidbar_set*.png`)대로: 검정 배경, 중앙 정렬.
  - 본문(흰 볼드): "보안을 위해 / 내부 네트워크에 / 연결된 상태로만 / 조회가 가능합니다."
  - 영문(회색): "For Security, Please connect to the private network before you proceed"
  - 하단 회색 알약 버튼: "내부 네트워크 연결하기 / Connect to the Network"
- 버튼 동작: 두 단계.
  1. 탭 → 매장 와이파이 이름(`wifi_ssid`)·비번(`wifi_password`)을 크게 표시(복사 버튼) + 연결 안내.
  2. "연결했어요 · 계속" 버튼 → `window.location.href = '/{slug}/enter'`(주소A 재진입 → IP 재확인).
  - `wifi_ssid` 미설정 매장이면 정보 단계 생략, 버튼이 바로 `/{slug}/enter`로 이동.
- props에 `slug` 추가. 렌더 지점 2곳(`layout.tsx`, `WifiRestrictionWrapper.tsx`)에서 `slug` 전달.

### 4. QR URL — `backend/menu_project/menu/api/views.py`(+ `qr_views.py`)
- `QRCodeView`의 `menu_url` 조립부: `/{slug}/` → `/{slug}/enter/`.
- 조건부 `?wifi=` 파라미터는 그대로 유지(뒤에 붙어 `/{slug}/enter/?wifi=...`가 됨). SSID 방식(method B)은 이번에 건드리지 않음.
- 레거시 `qr_views.py`도 일관성 위해 동일 변경(프론트는 미사용이나 혼란 방지).

## 동작 흐름

**QR 손님 (와이파이 연결됨):** QR 스캔 → `/{slug}/enter` → IP 통과 → 비디오 → `/{slug}` 메뉴.
**QR 손님 (와이파이 안 됨):** `/{slug}/enter` → IP 불일치 → 주소C → [내부 네트워크 연결하기] → 와이파이 정보 → 연결 → [계속] → `/{slug}/enter` 재진입 → 통과 → 비디오 → 메뉴.
**링크 손님 (와이파이 연결됨):** `/{slug}` → IP 통과 → 비디오 없이 메뉴.
**링크 손님 (와이파이 안 됨):** `/{slug}` → 주소C → (위와 동일 복구 흐름).

## 범위 밖 (YAGNI)
- SSID(`?wifi=`) 방식(`restrict_by_wifi_ssid`, `WifiRestrictionWrapper`) 로직.
- 인트로 쿨다운(`localStorage lastIntroTime`) — 주소A는 매번 재생, 메뉴는 자동재생 없음이라 무관.
- 카테고리 URL 구조.

## 테스트 계획 (develop, bid 매장)
1. `/bid/enter` 접속 → 비디오 재생 후 `/bid`로 이동 확인(Playwright).
2. `/bid` 직접 접속 → 인트로 비디오 오버레이 없음 확인.
3. `restrict_by_ip=True` + 틀린 IP → 주소C 새 디자인·문구 확인 → 버튼 탭 → 와이파이 정보 표시 → [계속] → `/bid/enter` 이동 확인. 검증 후 원복.
4. QR 인코딩 URL이 `/bid/enter/`인지 확인(QR API 응답 디코드 또는 코드 경로 검증).

## 위험 / 롤백
- 변경 대부분 프론트. QR URL 변경은 서버. develop 격리 검증 후 main 머지.
- 문제 시: QR URL 롤백(1줄), IntroManager `autoPlayIntro` 기본값이 true라 원복 쉬움.
