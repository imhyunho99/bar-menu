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
  1. 운영 DB(`bar_menu`)를 읽기 전용 보조 연결(Django 다중 DB, `prod` alias)로 연결. `.using('prod')`로 읽고 `default`(dev)에 쓴다. DATABASE_ROUTERS 불필요.
  2. 지정 slug의 객체 그래프를 dev DB로 복사. **삽입 순서:** Restaurant → SiteSettings → Category(top-level, `parent=None`) → Category(children, 자기참조) → MenuItem → MenuItemPairing.
  3. **미디어 파일 복사를 먼저** 하고(§ 하단 HAZARD 2), 그 다음 레코드를 쓴다. 파일은 `_meta.get_fields()`로 모든 `FileField`/`ImageField`를 **동적 순회**하여 참조 파일만 운영 media root → dev media root로 복사.
- **재시딩:** 같은 명령 재실행 시 dev의 해당 slug 데이터를 삭제 후 재삽입(PK 보존 — dev엔 bid만 있으므로 sorok과 충돌 없음). 이 방식이면 자기참조 `Category.parent`·`MenuItem.category` PK 재매핑 불필요.

**구현 시 반드시 처리할 함정 (리뷰에서 확인됨):**
- **HAZARD 1 — `post_save` 시그널이 SiteSettings 중복 생성.** `models.py:31-34` `create_restaurant_settings`가 Restaurant 생성 시 빈 SiteSettings를 자동 생성한다. SiteSettings→Restaurant가 **OneToOne이 아니라 FK(복수)**라 DB가 막지 않아 2개가 생기고, `QRCodeView`가 `.filter().first()`로 엉뚱한(빈) 걸 집을 수 있다. → 시딩 중 시그널을 disconnect 하거나, 자동 생성분을 삭제 후 복사, 또는 update-in-place.
- **HAZARD 2 — `.save()` 재호출 시 `optimize_image`가 파일명을 `.webp`로 재작성.** 각 모델 `save()`가 `utils.py:16-17` `optimize_image`를 호출해 파일을 재인코딩·개명한다. 재시딩마다 경로가 바뀌어 drift/orphan 발생. → 미디어 파일을 먼저 복사하고, 레코드는 `optimize_image`를 우회하여 쓴다(`bulk_create` 또는 `FileField.name` 직접 지정 + 시그널/최적화 bypass).
- **파일 필드 누락 주의:** SiteSettings에 **16개 파일 필드** — `logo_image`, `intro_image`, `intro_video`, `loading_video_2`, `side_image` + **`fonts/` 11개**(`models.py:149-212`). 그 외 `Category.category_image`, `MenuItem.menu_image`, `MenuItem.detail_image`, `MenuItemPairing.image`. 폰트·로딩영상이 가장 빠뜨리기 쉽다 → 하드코딩 금지, `_meta` 순회 필수.
- **collectstatic:** dev 체크아웃에서 `collectstatic` 실행 필요(WhiteNoise ManifestStorage `settings.py:185`). 누락 시 develop-api의 `/static` 500.

## 6. 중복 uwsgi 정리 + deploy.yml 교정 (선행, 운영에 영향 — 신중)

**리뷰로 밝혀진 실제 상황 (내가 앞서 말한 메모리 수치는 틀렸다):**
- `bar_menu.sock` 경로에 두 소켓이 바인딩돼 있고, **실제 nginx가 쓰는 inode는 `bidbar.service`가 소유**한다. emperor의 `bar_menu.ini` vassal은 **고아 리스너**(부팅 순서상 소켓 파일을 bidbar가 나중에 덮어씀).
- 이 vassal은 **거의 전부 swap out** 상태 → 제거해도 **RAM은 ~14MB만 확보**된다. "정리하면 dev 자리가 난다"는 내 앞선 설명은 과장이었다. 정리의 진짜 가치는 (a) 아래 deploy.yml 무동작 버그 교정, (b) 위험한 고아 vassal 제거다.

**STOP-SHIP: 스펙 원안대로 vassal을 그냥 지우면 운영 502 장애가 난다.** vassal `.ini`에 `vacuum = true`가 있어, emperor가 이 vassal을 멈추면 `unlink()`로 **지금 bidbar.service가 쓰는 실 소켓 파일을 삭제**한다(vacuum은 inode가 아니라 경로 기준). 그러면 nginx `connect()`가 `ENOENT` → 전 API 502, bidbar 수동 재시작 전까지 지속.

- **안전 조치 (무중단 방식, 권장):** `bidbar.service`와 nginx를 **새 소켓 경로**(`bar_menu_prod.sock`)로 옮긴다 → `restart bidbar` + `nginx -s reload` + `curl` 검증 → *그 다음* vassal 제거(이제 vacuum은 쓰이지 않는 옛 경로만 unlink → 무해).
- **차선 (짧은 blip 허용):** vassal `.ini`를 `vacuum = false`로 먼저 고쳐 reload → vassal 제거 → **즉시** `restart bidbar` + `curl` 검증.
- emperor의 다른 vassal(`bidbar_menu.ini`, `uwsgi.ini`=carlogo)은 **건드리지 않는다**.
- 롤백: `.ini` 복원 + `restart bidbar`.

### 6-1. deploy.yml 무동작 버그 (독립 실드, 반드시 교정)
`deploy.yml:35`의 `sudo systemctl restart uwsgi`는 **고아 emperor vassal을 재시작**할 뿐 실제 서빙 주체 `bidbar.service`를 재시작하지 않는다(`NRestarts=0`, auto-reload 없음). 즉 **2026-07-09 이후 백엔드 배포가 코드를 반영하지 못하는 잠재 무동작 상태.** 다음 `backend/**` push가 stale 코드를 배포하게 된다. → restart 대상을 `bidbar.service`로 변경. CI에 넣기 전에 **수동으로 한 번 재시작 + curl 검증**(bidbar.service는 지금껏 재시작된 적 없음). SSH 사용자 `ubuntu`는 `NOPASSWD: ALL`이라 sudo 동작 확인됨.

### 6-2. dev DB가 운영 DB로 오연결되는 위험 (STOP-SHIP)
`settings.py:134-136`이 `DB_NAME`을 **`bidbar_menu`(다른 프로젝트의 운영 DB)** 로 기본값 처리하고, 로컬 Postgres가 trust/빈 비밀번호 인증이다. dev 서비스가 `DB_NAME` 없이 뜨면 **운영 `bidbar_menu` DB에 붙어 손상**시킬 수 있다. (bidbar.service가 `.env` 없이 systemd `Environment=`만으로 도는 전례가 있어 `.env` 미로드 시 fallthrough 현실적.)
- **조치:** (a) dev systemd 유닛의 `Environment=`에 `DB_NAME`/`DB_USER`를 **명시 고정**(.env 의존 금지), (b) `settings.py`를 `DB_NAME` 미설정 시 **기동 실패(fail-fast)** 하도록 변경, (c) `bar_dev_user`에 `bar_menu_dev`만 권한 부여.

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

## 11. 안전 실행 순서 (리뷰 반영)

1. **베이스라인:** 운영 `curl` 정상 확인, `free -m` 기록, 실 소켓 소유자 재확인.
2. **dev 백엔드를 안전하게 설계:** `bar_menu_dev` DB + `bar_dev_user` 생성; `settings.py`를 `DB_NAME` 미설정 시 fail-fast; dev systemd 유닛에 DB env 고정(§6-2).
3. **deploy.yml 교정(§6-1):** restart 대상을 `bidbar.service`로. 먼저 수동 재시작 1회 + `curl` 검증.
4. **중복 vassal 정리(§6):** 무중단 소켓 스왑 방식 또는 vacuum-off+즉시재시작. 운영 검증, 롤백 대기. 저트래픽 시간대.
5. **dev uwsgi(1 worker, 하드 캡) + nginx `develop-api` 블록 + 인증서.**
6. **`seed_from_prod` 실행:** 저트래픽 시간대, `free -m`/swap 감시. 클론/collectstatic/미디어 복사는 transient로 200MB 수준까지 swap을 밀 수 있어 `nice`/`ionice`로 완화, dev worker는 `--processes 1 --max-requests` 등으로 캡.
7. **DNS 추가 후 Vercel preview 도메인 연결(마지막).**

## 12. 완료 기준

1. `dev` 브랜치 push 시 `develop.bar-menu.ddnsfree.com`에 자동 반영되고, bid 메뉴(폰트·로딩영상 포함)가 정상 렌더된다.
2. dev의 API/DB/미디어가 운영과 완전히 분리되어, dev에서의 쓰기가 운영 DB·media에 영향을 주지 않는다.
3. dev에서 주문/문의 테스트가 운영 데이터를 오염시키지 않는다.
4. 운영(`bar-menu.ddnsfree.com`)은 전 과정에서 무중단(§6 소켓 스왑으로 502 회피).
5. Analytics 대시보드에 방문 데이터가 잡힌다.
6. dev 백엔드 상주 상태에서 서버 `available` 메모리가 안정적이고, 클론 중 swap-thrash로 인한 운영 지연이 없다.
