> An install-free QR ordering and payment platform, running in production at a real dining pub (Bidbar). A Next.js 16 frontend and a Django REST Framework backend unified under one domain via an Nginx reverse proxy, with Wi-Fi-scoped ordering, Payhere POS integration, and a real-time order dashboard.

---

# bar-menu

매장 내 테이블에 비치된 QR 코드를 스캔하여, 별도의 앱 설치 없이 메뉴를 확인할 수 있는 프리미엄 웹 메뉴판 서비스입니다.

[Bidbar](https://naver.me/5ISHAhLZ)의 의뢰를 받아 제작되었으며, 현재 실제 매장에서 운영 중입니다.

> **Live** — [https://bar-menu.ddnsfree.com](https://bar-menu.ddnsfree.com)

---

## 아키텍처

```
┌─────────────┐       ┌──────────────────┐       ┌──────────────┐
│  Customer    │──────▶│  Vercel (Edge)   │──────▶│  OCI (Ubuntu) │
│  Mobile/Web  │       │  Next.js 16 SSR  │       │  Django REST  │
└─────────────┘       └──────────────────┘       │  PostgreSQL   │
                                                  │  Nginx+uWSGI  │
                                                  └──────────────┘
```

| Layer | Stack |
|-------|-------|
| **Frontend** | Next.js 16 (App Router, Server Components, Turbopack) |
| **Backend** | Django 5 · Django REST Framework · PostgreSQL |
| **Infra** | Vercel (프론트엔드 SSR) · Oracle Cloud (백엔드 API + Admin) |
| **Reverse Proxy** | Nginx (통합 도메인 라우팅 — Vercel ↔ uWSGI) |
| **SSL** | Certbot (Let's Encrypt) |

---

## 주요 기능

### 고객용

- **QR 코드 스캔** — 테이블별 고유 QR 스캔 시 메뉴판 자동 진입
- **카테고리 탐색** — 드래그 앤 드롭으로 정렬된 카테고리/서브카테고리 트리
- **메뉴 상세** — 이미지 라이트박스, 드링크 페어링 추천, 기타 사항 표시
- **검색** — 실시간 메뉴 검색, 결과 클릭 시 해당 카테고리로 이동 + 하이라이트 스크롤
- **장바구니** — 테이블 번호 입력 후 주문 (관리자 설정으로 On/Off 제어)
- **WiFi 도우미** — 매장 WiFi SSID/PW 안내 + 자동연결 QR 코드
- **스크린샷 차단** — 관리자 설정 시 우클릭/PrintScreen/DevTools 차단

### 관리자용

- **통합 어드민 대시보드** — Django Admin 기반 커스텀 UI
- **카테고리 트리 워크스페이스** — 네스티드 트리 + 드래그 앤 드롭 재정렬
- **메뉴 워크스페이스** — 대량 복제/삭제/이동, 품절 즉시 토글
- **주문 관리** — 실시간 주문 현황 (5초 폴링, 신규 주문 사운드 알림)
- **스타일 커스텀** — 메뉴명/가격/설명 등 폰트·색상·크기를 항목별로 개별 설정
- **QR 코드 생성** — 아치형 스탠드 디자인의 테이블 인쇄용 QR 페이지
- **WiFi 접속 제한** — 매장 IP 기반 또는 SSID 기반 접근 제어
- **Payhere POS 연동** — 주문 접수 시 Payhere API 자동 전송

---

## 프로젝트 구조

```
bar-menu/
├── backend/
│   ├── menu_project/
│   │   ├── menu/                  # 메인 Django 앱
│   │   │   ├── models.py          # Restaurant, Category, MenuItem, SiteSettings, Order
│   │   │   ├── admin.py           # 커스텀 Admin (워크스페이스, D&D)
│   │   │   ├── admin_views.py     # 주문 대시보드, 카테고리 폼
│   │   │   ├── api/
│   │   │   │   ├── views.py       # REST API 뷰 (레스토랑, 카테고리, 검색, 주문)
│   │   │   │   ├── serializers.py # DRF 시리얼라이저
│   │   │   │   └── urls.py
│   │   │   ├── qr_views.py        # QR 코드 생성 (StyledPilImage)
│   │   │   └── payhere_api.py     # Payhere POS API 연동
│   │   ├── menu_project/
│   │   │   ├── settings.py        # Django 설정 (환경변수 기반)
│   │   │   └── urls.py
│   │   └── uwsgi.ini
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── [restaurantSlug]/   # 동적 라우팅 (매장별)
│   │   │   │   ├── layout.tsx      # 레스토랑 레이아웃 (폰트, CSS 변수, WiFi 제한)
│   │   │   │   ├── page.tsx        # 매장 메인 (카테고리 그리드)
│   │   │   │   ├── category/[categoryId]/page.tsx
│   │   │   │   └── qr/page.tsx     # QR 인쇄 페이지
│   │   │   └── page.tsx            # 랜딩 페이지
│   │   ├── components/
│   │   │   ├── MenuCard.tsx        # 메뉴 카드 (이미지, 라이트박스, 장바구니)
│   │   │   ├── Cart.tsx            # 장바구니 사이드 드로어
│   │   │   ├── NavigationRemote.tsx # 하단 카테고리 이동 리모컨
│   │   │   ├── TopBar.tsx          # 상단 바 (로고, 검색)
│   │   │   ├── WifiHelper.tsx      # WiFi 안내 플로팅 버튼
│   │   │   ├── WifiRestrictionBlock.tsx
│   │   │   ├── WifiRestrictionWrapper.tsx
│   │   │   └── ScreenshotBlocker.tsx
│   │   ├── lib/
│   │   │   └── types.ts           # TypeScript 인터페이스
│   │   └── styles/
│   │       └── globals.css        # 전역 스타일 + CSS 변수
│   ├── public/                    # 정적 에셋 (로고, 리모컨 아이콘)
│   ├── vercel.json
│   └── package.json
├── .gitignore
├── run_local.sh                   # 로컬 개발 서버 실행 스크립트
└── README.md
```

---

## 로컬 개발 환경

### 사전 요구사항

- Python 3.11+
- Node.js 20+
- PostgreSQL (또는 SQLite — `USE_SQLITE=True`)

### 설정

```bash
# 1. 저장소 클론
git clone https://github.com/imhyunho99/bar-menu.git
cd bar-menu

# 2. 백엔드 환경 설정
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt

# 3. 환경변수 설정
cat > .env.local << 'EOF'
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
USE_SQLITE=True
CSRF_TRUSTED_ORIGINS=http://localhost:8000,http://localhost:3000
CORS_ALLOWED_ORIGINS=http://localhost:3000
EOF

# 4. Django 마이그레이션
venv/bin/python backend/menu_project/manage.py migrate

# 5. 프론트엔드 설치
cd frontend
npm install
cd ..

# 6. 개발 서버 실행
./run_local.sh
```

- **고객 메뉴판**: http://localhost:3000/{restaurant_slug}
- **Django Admin**: http://localhost:8000/admin/

---

## 배포

### Frontend (Vercel)

```bash
cd frontend
npx vercel build --prod --yes
npx vercel deploy --prebuilt --prod
```

### Backend (OCI)

```bash
# rsync로 코드 동기화 후 uwsgi 리로드
rsync -avz backend/menu_project/ server:/path/to/menu_project/
ssh server "touch /path/to/reload.txt"
```

---

## 보안

- `SECRET_KEY`, `DB_PASSWORD` 등 모든 시크릿은 환경변수로 관리
- 프로덕션 환경에서 `DEBUG=False`, HTTPS 보안 헤더 자동 활성화
- API Rate Limiting 적용 (100 req/min)
- CORS 허용 도메인 제한
- WiFi 접속 제한 기능 (IP 기반 / SSID 기반)

---

## 라이선스

Private repository — All rights reserved.
