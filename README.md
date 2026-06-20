# Bar-Menu (Decoupled Monorepo)

Bar-Menu는 매장 내 테이블에 부착된 QR 코드를 스캔하여 별도의 앱 설치 없이 메뉴를 확인하는 스마트 모바일 QR 메뉴판 서비스입니다.
이 프로젝트는 유지 보수 및 개발 편의성을 극대화하기 위해 모놀리식 구조에서 **백엔드(Django REST Framework)와 프론트엔드(Next.js)가 분리된 모노레포 구조**로 리팩토링되었습니다.

---

## 🏗️ 서비스 아키텍처

```
bar-menu/ (Monorepo)
├── backend/                  # Django REST Framework (API Server, Admin)
│   ├── menu_project/         # Django project root
│   │   ├── menu/             # Core business logic app (Model, Admin, API)
│   │   │   ├── api/          # REST API (Views, Serializers)
│   │   │   └── models.py     # Restaurant, Category, MenuItem, SiteSettings
│   │   └── menu_project/     # Settings & main routing
│   └── requirements.txt
│
└── frontend/                 # Next.js (Static-site App, Vercel)
    ├── src/
    │   ├── app/              # App Router ([restaurantSlug], layout, context)
    │   ├── components/       # TopBar, SideMenu, MenuCard, NavigationRemote, ContactForm
    │   ├── lib/              # API Client (api.ts), Styles generator (styles.ts)
    │   └── styles/           # CSS Custom properties & global rules
    ├── vercel.json
    └── package.json
```

- **Backend (OCI Server / Django REST Framework)**:
  - 매장 관리 및 대표 관리자 기능(Django Admin)을 지속적으로 담당합니다.
  - Vercel에 호스팅된 프론트엔드에 CORS가 적용된 RESTful API를 제공합니다.
  - 업로드된 이미지 자산은 OCI 서버에 보존되며 CORS 규칙을 통해 안전하게 공유됩니다.
- **Frontend (Vercel / Next.js)**:
  - 정적 페이지(SSG, ISR) 형태로 Vercel 상에 배포되어 로딩 속도와 트래픽 대응 능력이 극대화되었습니다.
  - API에서 전달된 매장 설정(SiteSettings)의 색상, 폰트 스타일 파라미터는 프론트엔드에서 **CSS Variables (Custom Properties)** 형태로 주입되어 실시간으로 반영됩니다.

---

## 🛠️ 기술 스택

### Backend
* Python (Django & Django REST Framework)
* Database (SQLite/PostgreSQL)
* CORS Headers (`django-cors-headers`)

### Frontend
* TypeScript / React / Next.js (App Router)
* Vanilla CSS & CSS Variables (디자인 최적화)

### CI/CD & Deploy
* **Backend**: GitHub Actions를 통한 OCI Server SSH 자동 배포 (`backend/**` 경로에 변경사항 발생 시에만 배포 트리거)
* **Frontend**: Vercel 연동 자동 빌드 및 엣지 캐싱 서빙 (`frontend/**` 변경 트리거)

---

## ⚡ 주요 리팩토링 개선 사항

1. **빌드 효율화**: Frontend와 Backend 코드가 분리되어, 백엔드 로직 수정 시 프론트엔드 정적 파일이 재빌드되는 비효율성을 완전 타파했습니다.
2. **동적 CSS 주입**: DB의 `SiteSettings`에서 50개 이상의 폰트, 불투명도, 색상 옵션을 가져와 클라이언트 브라우저 단에서 즉각 CSS Custom Properties로 치환 렌더링함으로써 API 기반 스타일 커스텀이 가능합니다.
3. **사용자 경험 최적화**:
   - **스마트 주류 페어링**: 메뉴 모달 하단에 카드로 추천 페어링 메뉴 노출.
   - **아치형 QR 프레임**: 둥근 모양의 유니크한 오프라인 QR 스탠딩 디자인 지원.
   - **자동 위치 복원**: 특정 메뉴 ID 앵커 혹은 target 파라미터 주소 진입 시 중앙으로 부드럽게 스크롤.

---

## 🚀 시작하기

### 1. 백엔드 실행
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd menu_project
python manage.py migrate
python manage.py runserver
```

### 2. 프론트엔드 실행
```bash
cd frontend
npm install
npm run dev
```

*로컬 개발 시 `.env.local` 파일 등을 생성하여 `NEXT_PUBLIC_API_URL`을 로컬 백엔드 주소(`http://localhost:8000`)로 설정해 주세요.*
