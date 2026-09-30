# IP 기반 매장 와이파이 게이트 복구 — 설계

- 날짜: 2026-07-22
- 브랜치: develop
- 상태: 승인됨

## 배경 / 문제

"매장 와이파이에 연결됐을 때만 메뉴판을 볼 수 있다"는 기능이 동작하지 않는다.

이 기능은 `SiteSettings.restrict_by_ip` + `store_public_ip` 로 구현돼 있다. 접속자의 공인 IP가 매장 공인 IP와 같으면(=매장 와이파이 경유) 통과, 다르면(=LTE·외부망) 차단하는 방식이다. 게이트 로직은 `frontend/src/app/[restaurantSlug]/layout.tsx:45-65` 의 Next.js 서버 컴포넌트에 이미 구현돼 있다.

**근본 원인:** `SiteSettingsSerializer.Meta.fields`(`backend/menu_project/menu/api/serializers.py:125-130`)에 `store_public_ip` 가 빠져 있다. API가 이 값을 프론트로 내려주지 않아 `settings.store_public_ip` 가 항상 `undefined` 가 되고, 게이트 조건 `restrict_by_ip && store_public_ip` 가 항상 falsy 로 평가돼 **아무도 차단되지 않는다.** (프론트 타입 `types.ts:31` 에는 선언돼 있어 컴파일은 통과 → 조용한 실패)

## 기술적 제약 (설계 근거)

웹 브라우저는 기기가 연결된 **와이파이 SSID 를 읽을 수 없다**(프라이버시 제약, 네이티브 앱만 가능). 따라서 "연결된 와이파이 이름을 대조"하는 방식은 구현 불가. 페이지가 "매장 와이파이에 연결된 상태"를 알 수 있는 유일한 웹 방법은 **공인 IP 대조**이며, 이것이 곧 방식 A다. 목표를 실현하는 올바른 도구는 IP 방식이다.

## 변경 사항

### 1. 백엔드 (핵심 수정)
`backend/menu_project/menu/api/serializers.py` — `SiteSettingsSerializer.Meta.fields` 목록에 `'store_public_ip'` 추가.

이것만으로 값이 프론트로 전달되고 기존 게이트 로직이 살아난다. 프론트 로직·타입 수정 불필요.

### 2. 프론트엔드 (보안 보강)
`frontend/src/app/[restaurantSlug]/layout.tsx` — 서버 컴포넌트에서 IP 대조를 마친 뒤, `RestaurantProvider`(클라이언트 컨텍스트)로 넘기기 전에 `settings.store_public_ip` 를 `null` 로 지운다.

이유:
1. **정보 노출 방지** — 매장 공인 IP 가 클라이언트 페이지 소스에 남지 않게.
2. **우회 방지** — 값이 노출되면 공격자가 `X-Forwarded-For` 헤더에 그 IP 를 넣어 게이트를 우회할 수 있다(코드가 X-F-F 첫 항목을 신뢰). 값을 감추면 우회 난이도가 올라간다.

IP 대조는 서버 컴포넌트에서만 필요하므로 클라이언트로 내려줄 이유가 없다.

## 동작 흐름 (완성 후)

1. 손님이 매장 와이파이에 연결 (기존 `WifiHelper` 자동연결 QR 사용 가능).
2. 메뉴 URL 접속 → Vercel 서버 컴포넌트가 접속자 공인 IP(`x-forwarded-for` 첫 항목)를 `store_public_ip` 와 대조.
3. 일치 → 메뉴 표시 / 불일치 → `WifiRestrictionBlock` 락스크린("와이파이 접속 후 사용해 주세요").
4. `/qr` 페이지(`x-pathname` 헤더로 판별)와 localhost/`::1` 은 기존대로 예외.

## 범위 밖 (YAGNI)

- `restrict_by_wifi_ssid`(QR `?wifi=` 파라미터 방식, 방식 B)는 이번에 건드리지 않는다.
- 매장 공인 IP 자동 저장 로직(`admin_views.py:282`, 관리자 주문페이지 접속 시 자동 등록)은 이미 존재하며 유동 IP 변경 완화책으로 그대로 활용.

## 테스트 계획 (develop 환경, 운영 격리)

dev 환경: 프론트 `develop.bar-menu.ddnsfree.com`(Vercel), API `devapi.bar-menu.ddnsfree.com`(OCI), 시딩 매장 `bid`.

1. develop 브랜치에 커밋·푸시 → devapi(백엔드) + develop 프론트 자동 배포.
2. dev `bid` 매장 `SiteSettings`: `restrict_by_ip=True`, `restrict_by_wifi_ssid=False` 로 설정.
3. **차단 케이스:** `store_public_ip` 를 틀린 IP(예: `1.2.3.4`)로 설정 → `develop.bar-menu.ddnsfree.com/bid` 접속 시 락스크린 확인.
4. **통과 케이스:** `store_public_ip` 를 내 실제 공인 IP 로 설정 → 접속 시 메뉴 정상 표시 확인.
5. 클라이언트 페이로드에 `store_public_ip` 가 노출되지 않는지 확인(HTML 소스/RSC 페이로드에서 값 부재).

설정 변경은 dev Django admin(`devapi.../admin/`) 또는 dev 서버의 Django shell(SSH)로 수행. 운영(main)에는 영향 없음.

## 위험 / 롤백

- 변경이 작고 develop 격리 환경에서 검증 후 main 머지. 문제 시 `restrict_by_ip=False` 토글만으로 즉시 게이트 비활성(코드 롤백 불필요).
