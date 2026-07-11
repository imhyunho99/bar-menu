# 개발(develop) 테스트 환경 구축 설계

**작성일:** 2026-07-11
**목표:** 로컬 → 운영 직배포로 인해 에러가 운영에 노출되는 문제를 막기 위해, 운영과 격리된 테스트 환경 `develop.bar-menu.ddnsfree.com`을 구축한다. 더불어 방문자 집계를 위한 Vercel Analytics를 도입한다.

---

## 1. 배경 / 문제

- 현재 개발 흐름: 로컬 작업 → `main` push → 운영 자동 배포. 중간 검증 단계가 없다.
- 최근 사고 이력(`static page compile failure`, `font color rendering`, `scroll jumping`, 카테고리 토글 등)은 대부분 **프론트엔드 런타임/렌더링 문제**다.
- 현재 아키텍처(2026-07-09 컷오버 후): `bar-menu.ddnsfree.com` → Vercel, `api.bar-menu.ddnsfree.com` → OCI Django. 상세는 `memory/frontend_hosting_architecture.md`.

## 2. 작업 흐름 (git flow)

```
dev 브랜치에서 개발 → push → develop.bar-menu.ddnsfree.com 에서 검증
                                    ↓ 확인되면
                       dev → main 머지 → 운영 배포
```

- `dev` 브랜치를 신설한다. 이후 로컬 작업의 기본 브랜치는 `dev`.
- `main`은 "검증 완료된 것만" 들어가는 브랜치가 된다.

## 3. 프론트엔드 (Vercel — 서버 부하 0)

- Vercel `fe` 프로젝트는 모든 브랜치를 자동 빌드한다. `develop.bar-menu.ddnsfree.com` 도메인을 **`dev` 브랜치에 배정**한다.
- 환경변수 `NEXT_PUBLIC_API_URL`을 **Preview 환경에만** `https://develop-api.bar-menu.ddnsfree.com`으로 설정한다. Production 환경은 `https://api.bar-menu.ddnsfree.com` 유지.
  - `NEXT_PUBLIC_*`은 빌드타임 인라인 → dev 브랜치 빌드는 Preview 값을 사용한다.
- **검증 필요(구현 시):** `ddnsfree.com`이 Public Suffix라 `develop.` 서브도메인이 Vercel에서 CNAME으로 잡히는지 A레코드인지 확인 후 DNS 결정.

## 4. 백엔드 (OCI — 같은 코드, 완전 격리)

운영과 **DB·미디어 모두 격리**한다. `MEDIA_ROOT = BASE_DIR / 'media'`가 하드코딩이므로, dev는 **별도 체크아웃**으로 두어 media 폴더가 자연히 분리되게 한다.

- **위치:** `~/bar_menu_dev/` — `dev` 브랜치 체크아웃.
- **DB:** `bar_menu_dev` (신규 Postgres database, 같은 인스턴스). `DB_USER`는 기존 `bar_user` 재사용 또는 `bar_dev_user` 신설.
- **미디어:** `~/bar_menu_dev/menu_project/media/` (dev 전용). bid가 참조하는 파일만 복사한다.
- **uwsgi:** 경량 설정 `--processes 1 --threads 2` (~50MB 목표). 별도 소켓 `bar_menu_dev.sock`.
- **환경변수(`~/bar_menu_dev/.env`):**
  - `DB_NAME=bar_menu_dev`
  - `DJANGO_ALLOWED_HOSTS=develop-api.bar-menu.ddnsfree.com`
  - `CSRF_TRUSTED_ORIGINS=https://develop-api.bar-menu.ddnsfree.com,https://develop.bar-menu.ddnsfree.com`
  - `CORS_ALLOWED_ORIGINS=https://develop.bar-menu.ddnsfree.com`
  - `DJANGO_DEBUG=False`
- **nginx:** 신규 server block `develop-api.bar-menu.ddnsfree.com` → dev 소켓 + `/media`(dev 폴더) + `/static`(dev) + `/admin`. 폰트 CORS 헤더(`Access-Control-Allow-Origin`)는 운영과 동일하게 적용. Let's Encrypt 인증서 발급.

## 5. bid-only 시딩 (`seed_from_prod` 관리 명령)

재사용 가능한 Django 관리 명령을 신설한다: `python manage.py seed_from_prod --slug bid`

- **동작:**
  1. 운영 DB(`bar_menu`)를 읽기 전용 보조 연결(Django 다중 DB, `prod` alias)로 연결.
  2. 지정 slug(`bid`) 식당의 객체 그래프(Restaurant, SiteSettings, Category 계층, MenuItem, Pairing 등 관련 전체)를 dev DB(default)로 복사. 기존 dev 데이터는 해당 slug 범위에서 교체(idempotent).
  3. 복사된 레코드의 File/Image 필드를 순회하여 참조하는 미디어 파일만 운영 media root → dev media root로 복사.
- **재시딩:** 같은 명령 재실행으로 최신 운영 데이터를 다시 당겨온다.
- **주의(구현 시 검증):** 모델 간 FK 의존 순서, 파일 필드 누락 없이 전 모델 순회, dev DB의 기존 bid 데이터 정리 방식.

## 6. 메모리 안전장치 (선행 작업, 운영에 영향)

현재 서버 `available` ≈ 231MB로 빠듯하다. dev 백엔드를 얹기 전에 **중복 uwsgi를 정리**한다.

- 현재 `bar_menu` Django가 `bidbar.service`와 emperor의 `bar_menu.ini` vassal **양쪽에서 중복 실행** 중 (같은 소켓 경합). 상세는 `memory/uwsgi_service_duplication.md`.
- **조치:** emperor의 **`bar_menu.ini` vassal만 제거**하여 중복을 없앤다. `bidbar.service`가 단독 서빙. emperor의 다른 vassal(`bidbar_menu.ini`, `uwsgi.ini`=carlogo)은 **건드리지 않는다**.
- **부수 효과:** `deploy.yml`이 `sudo systemctl restart uwsgi`(emperor)를 재시작하던 버그를 함께 교정 — 실제 서빙 주체(`bidbar.service`)를 재시작하도록 변경.
- **위험:** 운영 서빙 프로세스를 건드리므로 독립 단계로 분리하고, 각 단계 후 운영 정상 확인 + 롤백 절차를 둔다.

## 7. 배포 자동화

- **프론트:** `dev` push → Vercel 자동 배포 (추가 설정 없음).
- **백엔드:** 신규 GitHub Actions 워크플로. `dev` 브랜치 + `backend/**` push → dev 인스턴스 배포(git pull `~/bar_menu_dev` → dev DB migrate → dev uwsgi restart). 운영 배포(`deploy.yml`)는 `main`만 유지.

## 8. Vercel Analytics (별개, 저위험)

- `@vercel/analytics` 설치, `src/app/layout.tsx`에 `<Analytics />` 추가.
- 운영·dev 양쪽에서 방문자·페이지뷰 집계 (Hobby 무료).

## 9. DNS (Dynu, domain id 13846236)

- `develop-api.bar-menu.ddnsfree.com` → A → `140.245.71.233` (OCI)
- `develop.bar-menu.ddnsfree.com` → Vercel (A 또는 CNAME, §3에서 확정), TTL 120

## 10. 범위 밖 (YAGNI)

- 운영 DB 실시간 동기화 (수동 재시딩으로 충분).
- dev 전용 Postgres 인스턴스 (같은 인스턴스 내 별도 database로 충분).
- sorok 식당 데이터 (bid만 시딩).

## 11. 완료 기준

1. `dev` 브랜치 push 시 `develop.bar-menu.ddnsfree.com`에 자동 반영되고, bid 메뉴가 정상 렌더된다.
2. dev의 API/DB/미디어가 운영과 완전히 분리되어, dev에서의 쓰기가 운영 DB·media에 영향을 주지 않는다.
3. dev에서 주문/문의 테스트가 운영 데이터를 오염시키지 않는다.
4. 운영(`bar-menu.ddnsfree.com`)은 전 과정에서 무중단.
5. Analytics 대시보드에 방문 데이터가 잡힌다.
6. 중복 uwsgi 정리 후 서버 `available` 메모리가 dev 백엔드 상주 상태에서도 안정적이다.
