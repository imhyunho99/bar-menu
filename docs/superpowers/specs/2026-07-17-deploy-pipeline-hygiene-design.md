# 배포 파이프라인 위생 정리 설계

작성일: 2026-07-17
브랜치: develop
상태: Phase 1 승인됨. Phase 2·3은 미승인(별도 판단).

## 배경

배포 파이프라인을 점검하다 두 가지 문제를 발견했다. 하나는 스테이징이 운영을 오염시킬 수 있는 경로이고, 다른 하나는 운영 배포가 한 달간 사실상 동작하지 않고 있었다는 것이다.

### 발견 1: develop 배포가 운영 런타임을 바꿀 수 있다

`deploy-develop.yml`은 `~/bar_menu/venv`를 활성화한 뒤 `pip install -r backend/requirements.txt`를 실행한다. 그런데 운영 서비스가 같은 venv를 쓴다.

```
bidbar.service ExecStart=/home/ubuntu/bar_menu/venv/bin/uwsgi ...
```

서버에 venv는 `~/bar_menu/venv` 하나뿐이다(`~/bar_menu/backend/venv`, `~/bar_menu_dev/venv` 모두 부재). 코드·DB·systemd 서비스·소켓·nginx server_name·Vercel 도메인은 모두 격리돼 있으나 **파이썬 런타임만 공유**한다.

`requirements.txt`의 `uwsgi>=2.0.20`은 핀이 없다. develop 배포가 운영이 실행 중인 uwsgi 바이너리 자체를 덮어쓸 수 있다.

2026-07-17 시점 확인 결과 **오염은 아직 실현되지 않았다.** 공유 venv 설치 목록이 운영 requirements.txt와 정확히 일치한다(Django 5.2.7, uWSGI 2.0.31, sentry-sdk 2.58.0 등). 위험은 잠재적이다.

### 발견 2: `deploy.yml`이 세 군데에서 조용히 실패한다

| 위치 | 문제 |
|---|---|
| `cd backend` → `source venv/bin/activate` | `~/bar_menu/backend/venv` 부재 → 활성화 실패 |
| `python manage.py migrate` | 서버에 `python3`만 존재, `python` 부재 → migrate·collectstatic이 실행된 적 없음 |
| `sudo systemctl restart uwsgi` | emperor 재시작. 실서빙 주체는 `bidbar.service` → 코드 미반영 |

appleboy/ssh-action의 `script_stop` 기본값이 false이고 스크립트 마지막 줄이 `echo "✓ ... completed successfully!"`라서 **모든 실행이 무조건 초록불로 끝난다.** 최근 8회 연속 success는 전부 거짓이다.

실질적으로 `deploy.yml`이 수행한 일은 `git reset --hard origin/main` 하나뿐이다.

증거:
- `bidbar.service`가 2026-07-09 12:22 기동 후 1주일 넘게 재시작 없음
- 운영 체크아웃 HEAD = `27da754`(2026-07-08), 마지막 백엔드 배포 실행일과 일치
- 미적용 마이그레이션 0건(45개 전부 적용) — 현재는 우연히 정합

### 발견 3: 기타 위생 문제

- **고아 uwsgi vassal**: emperor의 `/etc/uwsgi/vassals/bar_menu.ini`(PID 3906978)가 unlink된 소켓에 붙어 좀비 상태. RAM 956MB 중 274MB만 여유. emperor에는 `bidbar_menu.ini`·`uwsgi.ini`(타 프로젝트)가 얹혀 있어 **emperor 자체를 죽이면 안 된다.**
- **죽은 리포 파일**: `backend/Procfile`(gunicorn 명시, 실제는 uwsgi), `backend/menu_project/uwsgi.ini`(소켓·venv 경로가 실제와 불일치. 진짜 설정은 서버의 `/etc/uwsgi/vassals/bar_menu.ini`)
- **죽은 서버 .env**: `~/bar_menu/backend/.env`(2026-06-06)에 `USE_SQLITE` 존재. settings.py가 루트 `.env`를 먼저 로드하므로 현재는 무해하나, 루트 `.env` 부재 시 운영이 SQLite로 조용히 폴백하는 지뢰.

## 설계 원칙

**브랜치는 서버를 격리하지 않는다.** 운영과 dev가 같은 물리 서버 한 대에 얹혀 있으므로, systemd·vassal·venv 작업은 어느 브랜치에서 하든 즉시 운영에 영향을 준다. 따라서 작업을 "운영 무영향"과 "운영 영향"으로 갈라 단계를 나눈다.

## Phase 1 — 운영 무영향 (승인됨)

### 목표

develop→운영 오염 경로를 끊고, 리포의 고장·죽은 파일을 정리한다. 운영 프로세스는 건드리지 않는다.

### 순서

서버 작업이 리포 push보다 **먼저** 와야 한다. dev venv가 존재해야 그 다음 develop 배포가 공유 venv를 건드리지 않는다.

#### 1-A. 서버: dev 전용 venv 생성 (추가 작업, 운영 무영향)

```bash
python3 -m venv ~/bar_menu_dev/venv
~/bar_menu_dev/venv/bin/pip install -U pip
~/bar_menu_dev/venv/bin/pip install -r ~/bar_menu_dev/backend/requirements.txt
```

디스크 여유 29G 확인됨. venv 약 250MB. 프로세스 수가 늘지 않으므로 RAM 영향 없음.

#### 1-B. 서버: `bar_menu_dev.service` ExecStart 전환

```
ExecStart=/home/ubuntu/bar_menu/venv/bin/uwsgi \      # 변경 전
ExecStart=/home/ubuntu/bar_menu_dev/venv/bin/uwsgi \  # 변경 후
```

이 단계를 빠뜨리면 dev venv를 만들어도 dev가 운영 바이너리로 계속 뜬다. 유닛 파일 백업 후 `daemon-reload` + `restart bar_menu_dev`. dev만 재시작되므로 운영 무영향.

#### 1-C. 리포: `deploy-develop.yml` 수정

- `source ~/bar_menu/venv/bin/activate` → `source ~/bar_menu_dev/venv/bin/activate`
- `script_stop: true` 추가

#### 1-D. 리포: `deploy.yml` 수리 (휴면 커밋)

이 워크플로우는 `push: branches: [main]`에서만 트리거되므로, develop에 커밋해도 발효되지 않는다. Phase 3에서 처음 동작한다.

```yaml
    script_stop: true
    script: |
      cd ~/bar_menu
      git fetch origin main
      git reset --hard origin/main
      source ~/bar_menu/venv/bin/activate
      pip install -q -r backend/requirements.txt
      cd backend/menu_project
      python manage.py migrate --noinput
      python manage.py collectstatic --noinput
      sudo systemctl restart bidbar
```

변경점 네 가지:
1. `script_stop: true` — 중간 실패가 red로 드러난다
2. venv 경로를 `~/bar_menu/venv`로 교정 (activate 성공 후 `python`이 해결되므로 migrate도 살아난다)
3. 재시작 대상을 `uwsgi`(emperor) → `bidbar`(실서비스)로 교정
4. 마지막 `echo "✓ ... completed successfully!"` 삭제 — 실패를 초록불로 덮어온 원인

#### 1-E. 리포: `uwsgi` 핀 + 죽은 파일 삭제

- `requirements.txt`: `uwsgi>=2.0.20` → `uwsgi==2.0.31` (현재 설치 버전)
- 삭제: `backend/Procfile`, `backend/menu_project/uwsgi.ini`

### 검증

핵심 회귀 테스트는 **develop 배포 후 공유 venv가 불변인지**다. Phase 1의 `requirements.txt` 변경 자체가 이 테스트를 유발한다.

기준선(2026-07-17 측정):
```
~/bar_menu/venv/bin/pip freeze | sha256sum
54c8f82dc9cb876f45844d62ed1c2e9d44eb3b05eb1163bfbae16de14f207a67
```

| 항목 | 기대 |
|---|---|
| develop push 후 공유 venv 해시 | `54c8f82d…` 그대로 (불변) |
| dev venv에 uwsgi==2.0.31 설치 | 확인됨 |
| `bar_menu_dev.service` 실행 바이너리 | `~/bar_menu_dev/venv/bin/uwsgi` |
| `https://devapi.bar-menu.ddnsfree.com` | 200 |
| `https://api.bar-menu.ddnsfree.com` | 200 (무영향) |
| `bidbar.service` 기동 시각 | 2026-07-09 그대로 (재시작 없음) |
| `deploy-develop.yml` 실행 결과 | green |

### 롤백

- 리포: `git revert`
- `bar_menu_dev.service`: 백업 유닛 복원 + `daemon-reload` + restart
- dev venv: 디렉토리 삭제(운영 무관)

운영을 건드리지 않으므로 Phase 1의 롤백은 운영 리스크가 없다.

## Phase 2 — 운영 영향, 별도 승인 필요 (미승인)

브랜치와 무관하며 트래픽이 적은 점검창이 필요하다. Phase 1·3과 독립적으로 언제든 실행 가능.

1. `/etc/uwsgi/vassals/bar_menu.ini` 백업 후 제거 → emperor 재시작(타 프로젝트 vassal 유지) → `bidbar` 재시작해 소켓 단독 점유
2. `~/bar_menu/backend/.env` 격리 (`USE_SQLITE` 폴백 지뢰 제거)

리스크는 낮다. 재시작 시 로드되는 코드가 현재 구동 중인 코드와 동일하고(체크아웃 `27da754`가 프로세스 기동 07-09보다 앞섬), venv도 requirements와 정합함이 확인됐다. 그럼에도 운영 재시작이므로 별도 승인 대상으로 남긴다.

기대 효과: 고아 프로세스 정리로 RAM 회수, `deploy.yml`의 재시작 대상과 실제 서빙 주체 일치.

## Phase 3 — develop → main 머지 (미승인)

수리된 `deploy.yml`이 발효되며 한 달 만의 첫 실제 배포가 실행된다. migrate·collectstatic·`bidbar` 재시작이 모두 진짜로 돈다.

머지 시 운영에 반영될 백엔드 변경(develop↔main 차이):
- `menu/management/commands/seed_from_prod.py` (신규)
- `menu_project/settings.py` — `DB_NAME` fail-fast

`DB_NAME` fail-fast는 운영 `~/bar_menu/.env`에 `DB_NAME`이 존재함을 확인했으므로 안전하다. 미적용 마이그레이션도 0건이라 사실상 no-op으로 예상되나, 첫 실제 배포이므로 실행을 지켜봐야 한다.

Phase 2를 Phase 3보다 먼저 하는 것이 바람직하다. 필수는 아니다 — vassal은 `vacuum` 동작으로 계속 고아 상태에 머물러 `bidbar` 재시작과 경합하지 않는다.

## 범위 밖

- `bidbar` vs `bar_menu` 네이밍 통일, emperor 전면 재구성 — 타 프로젝트 영향 범위가 커서 제외
- `run_local.sh` — 로컬 전용, 실사용 여부 미확인
- Sentry DSN의 서버 `.env` 설정 — 별도 작업
