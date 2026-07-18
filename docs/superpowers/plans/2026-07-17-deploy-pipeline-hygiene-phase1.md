# Phase 1 배포 파이프라인 위생 정리 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** develop 배포가 운영 파이썬 런타임을 오염시킬 수 있는 경로를 끊고, 리포의 고장난 워크플로우와 죽은 파일을 정리한다. 운영 프로세스는 건드리지 않는다.

**Architecture:** 서버에 dev 전용 venv를 만들어 스테이징을 운영 런타임에서 분리한 뒤, 리포 워크플로우가 그 venv를 쓰도록 전환한다. `deploy.yml` 수리는 `push: branches: [main]` 트리거라 develop 커밋 시 휴면 상태로 남는다. 검증은 유닛 테스트가 아니라 **서버 실측**이다 — 공유 venv 해시 불변이 핵심 회귀 테스트다.

**Tech Stack:** GitHub Actions (appleboy/ssh-action@v1.0.0), systemd, uWSGI, Python venv, Django 5.2.7

## Global Constraints

- **운영 무영향이 Phase 1의 정의다.** `~/bar_menu`, `bidbar.service`, `~/bar_menu/venv`를 수정하는 명령은 이 계획에 없다. 읽기만 한다.
- 공유 venv 기준선 해시는 `54c8f82dc9cb876f45844d62ed1c2e9d44eb3b05eb1163bfbae16de14f207a67` (`~/bar_menu/venv/bin/pip freeze | sha256sum`, 2026-07-17 측정). 모든 태스크 종료 시 불변이어야 한다.
- `bidbar.service` 기동 시각 `2026-07-09 12:22:09 KST` 불변. 재시작이 일어나면 Phase 1 위반이다.
- emperor(`uwsgi.service`)와 타 프로젝트 vassal(`bidbar_menu.ini`, `uwsgi.ini`)은 건드리지 않는다. Phase 2 범위다.
- SSH 접속: `ssh -i ~/.ssh/deploy_test.key ubuntu@140.245.71.233`
- 작업 브랜치: `develop`. main에 직접 push 금지.
- `deploy-develop.yml`의 트리거 경로는 `backend/**`와 `.github/workflows/deploy-develop.yml`이다. 어떤 파일을 push하느냐가 배포 발생 여부를 결정하므로 태스크마다 명시한다.

---

### Task 1: 서버에 dev 전용 venv 구축 + dev 서비스 전환

**Files:**
- Create (서버): `/home/ubuntu/bar_menu_dev/venv/`
- Modify (서버): `/etc/systemd/system/bar_menu_dev.service` — `ExecStart` 1줄
- Backup (서버): `/root/bar_menu_dev.service.bak.2026-07-17`

**Interfaces:**
- Consumes: `~/bar_menu_dev/backend/requirements.txt` (develop 체크아웃)
- Produces: `/home/ubuntu/bar_menu_dev/venv/bin/uwsgi`, `/home/ubuntu/bar_menu_dev/venv/bin/python` — Task 2의 `deploy-develop.yml`이 이 경로를 activate 한다.

리포 변경 없음. 커밋 없음. 서버 상태만 바뀐다.

- [ ] **Step 1: 작업 전 기준선 기록**

```bash
ssh -i ~/.ssh/deploy_test.key ubuntu@140.245.71.233 'echo "shared venv: $(~/bar_menu/venv/bin/pip freeze | sha256sum | cut -d" " -f1)"; echo "bidbar since: $(systemctl show bidbar -p ActiveEnterTimestamp --value)"; df -h / | tail -1'
```

Expected: shared venv 해시가 `54c8f82d…`로 시작. bidbar since가 `2026-07-09 12:22:09 KST`. 디스크 여유 20G 이상.

기준선이 다르면 **중단하고 보고한다.** 누군가 그 사이 서버를 건드린 것이므로 계획의 전제가 깨진다.

- [ ] **Step 2: dev venv 생성**

```bash
ssh -i ~/.ssh/deploy_test.key ubuntu@140.245.71.233 'python3 -m venv ~/bar_menu_dev/venv && ~/bar_menu_dev/venv/bin/pip install -q -U pip && ~/bar_menu_dev/venv/bin/pip install -q -r ~/bar_menu_dev/backend/requirements.txt && ~/bar_menu_dev/venv/bin/pip list | grep -iE "django|uwsgi|sentry"'
```

Expected: `Django 5.2.7`, `uWSGI 2.0.31`, `sentry-sdk 2.58.0` 출력. 약 1~2분 소요.

실패 시(`python3 -m venv` 오류) `python3-venv` 패키지 부재를 의심한다. 그 경우 `sudo apt-get install -y python3-venv` 후 재시도.

- [ ] **Step 3: dev venv가 운영과 독립인지 확인**

```bash
ssh -i ~/.ssh/deploy_test.key ubuntu@140.245.71.233 'echo "dev  : $(~/bar_menu_dev/venv/bin/python -c "import sys; print(sys.prefix)")"; echo "prod : $(~/bar_menu/venv/bin/python -c "import sys; print(sys.prefix)")"; echo "shared venv now: $(~/bar_menu/venv/bin/pip freeze | sha256sum | cut -d" " -f1)"'
```

Expected: dev가 `/home/ubuntu/bar_menu_dev/venv`, prod가 `/home/ubuntu/bar_menu/venv`. **공유 venv 해시는 `54c8f82d…` 그대로** — venv 생성이 운영을 건드리지 않았음을 증명한다.

- [ ] **Step 4: 유닛 파일 백업**

```bash
ssh -i ~/.ssh/deploy_test.key ubuntu@140.245.71.233 'sudo cp /etc/systemd/system/bar_menu_dev.service /root/bar_menu_dev.service.bak.2026-07-17 && sudo ls -la /root/bar_menu_dev.service.bak.2026-07-17'
```

Expected: 백업 파일이 존재. 롤백 경로 확보 전에는 유닛을 수정하지 않는다.

- [ ] **Step 5: ExecStart를 dev venv로 전환**

```bash
ssh -i ~/.ssh/deploy_test.key ubuntu@140.245.71.233 'sudo sed -i "s|^ExecStart=/home/ubuntu/bar_menu/venv/bin/uwsgi|ExecStart=/home/ubuntu/bar_menu_dev/venv/bin/uwsgi|" /etc/systemd/system/bar_menu_dev.service && grep ExecStart /etc/systemd/system/bar_menu_dev.service'
```

Expected: `ExecStart=/home/ubuntu/bar_menu_dev/venv/bin/uwsgi \`

`^ExecStart=` 앵커와 정확한 전체 경로 매칭이라 이 한 줄만 바뀐다. `bar_menu_dev.service` 파일만 대상이므로 `bidbar.service`는 영향받지 않는다.

- [ ] **Step 6: dev 서비스만 재시작**

```bash
ssh -i ~/.ssh/deploy_test.key ubuntu@140.245.71.233 'sudo systemctl daemon-reload && sudo systemctl restart bar_menu_dev && sleep 3 && systemctl is-active bar_menu_dev'
```

Expected: `active`

- [ ] **Step 7: dev가 자체 venv 바이너리로 뜨는지 실측**

```bash
ssh -i ~/.ssh/deploy_test.key ubuntu@140.245.71.233 'echo "=== dev 프로세스 ==="; ps -o cmd -C uwsgi | grep bar_menu_dev | head -1; echo "=== 운영 무영향 확인 ==="; echo "bidbar since: $(systemctl show bidbar -p ActiveEnterTimestamp --value)"; echo "shared venv : $(~/bar_menu/venv/bin/pip freeze | sha256sum | cut -d" " -f1)"'
```

Expected:
- dev 프로세스 명령줄이 `/home/ubuntu/bar_menu_dev/venv/bin/uwsgi`로 시작
- `bidbar since` = `2026-07-09 12:22:09 KST` (불변)
- shared venv = `54c8f82d…` (불변)

- [ ] **Step 8: dev API 응답 확인**

```bash
curl -s -o /dev/null -w "devapi: %{http_code}\n" https://devapi.bar-menu.ddnsfree.com/admin/login/
curl -s -o /dev/null -w "prod  : %{http_code}\n" https://api.bar-menu.ddnsfree.com/admin/login/
```

Expected: 둘 다 `200`. dev가 새 venv로 정상 서빙하고 운영도 멀쩡하다.

dev가 5xx면 Step 4의 백업을 복원한다:
```bash
ssh -i ~/.ssh/deploy_test.key ubuntu@140.245.71.233 'sudo cp /root/bar_menu_dev.service.bak.2026-07-17 /etc/systemd/system/bar_menu_dev.service && sudo systemctl daemon-reload && sudo systemctl restart bar_menu_dev'
```

---

### Task 2: `deploy-develop.yml`을 dev venv로 전환

**Files:**
- Modify: `.github/workflows/deploy-develop.yml:24-35`

**Interfaces:**
- Consumes: Task 1이 만든 `/home/ubuntu/bar_menu_dev/venv/bin/activate`
- Produces: dev venv만 건드리는 배포 파이프라인. Task 4의 회귀 테스트가 이것에 의존한다.

이 파일 자체가 트리거 경로에 있으므로 **push 시 배포가 실행된다.** 그게 이 태스크의 테스트다.

- [ ] **Step 1: 워크플로우 수정**

`.github/workflows/deploy-develop.yml`에서 `with:` 블록에 `script_stop: true`를 추가하고 venv 경로를 바꾼다. 최종 형태:

```yaml
    - name: Deploy backend to develop instance
      uses: appleboy/ssh-action@v1.0.0
      with:
        host: ${{ secrets.SSH_HOST }}
        username: ${{ secrets.SSH_USER }}
        key: ${{ secrets.SSH_PRIVATE_KEY }}
        script_stop: true
        script: |
          cd ~/bar_menu_dev
          git fetch origin develop
          git reset --hard origin/develop
          source ~/bar_menu_dev/venv/bin/activate
          pip install -q -r backend/requirements.txt
          cd backend/menu_project
          python manage.py migrate --noinput
          python manage.py collectstatic --noinput
          sudo systemctl restart bar_menu_dev
```

변경점은 세 개다. `script_stop: true` 추가(중간 실패가 red로 드러난다), `source ~/bar_menu/venv/bin/activate` → `~/bar_menu_dev/venv`, 그리고 마지막 `echo "✓ Develop backend deployment completed!"` 줄 삭제 — `script_stop: true`가 있어도 성공 echo는 실패를 덮는 습관을 남긴다.

- [ ] **Step 2: 배포 전 기준선 재확인**

```bash
ssh -i ~/.ssh/deploy_test.key ubuntu@140.245.71.233 '~/bar_menu/venv/bin/pip freeze | sha256sum | cut -d" " -f1'
```

Expected: `54c8f82d…`. 이 값을 Step 5에서 대조한다.

- [ ] **Step 3: 커밋**

```bash
git add .github/workflows/deploy-develop.yml
git commit -m "ci: run develop deploy in its own venv

deploy-develop.yml activated ~/bar_menu/venv and pip installed into it.
bidbar.service (production) runs from that same venv, so a develop
deploy could mutate the production runtime. Point it at the dedicated
~/bar_menu_dev/venv instead.

Also set script_stop: true and drop the trailing success echo, which
together made every run report green regardless of what failed."
```

- [ ] **Step 4: push — 배포 발생**

```bash
git push origin develop
gh run watch $(gh run list --workflow=deploy-develop.yml --limit 1 --json databaseId --jq '.[0].databaseId')
```

Expected: workflow가 **green**으로 완료. `script_stop: true` 하에서의 green은 이제 진짜다.

red가 나면 로그를 읽는다. 이건 진전이다 — 그동안 숨어 있던 실패가 처음 드러난 것일 수 있다.

- [ ] **Step 5: 회귀 테스트 — 공유 venv 불변 확인**

```bash
ssh -i ~/.ssh/deploy_test.key ubuntu@140.245.71.233 'echo "shared venv: $(~/bar_menu/venv/bin/pip freeze | sha256sum | cut -d" " -f1)"; echo "bidbar since: $(systemctl show bidbar -p ActiveEnterTimestamp --value)"; echo "dev 프로세스:"; ps -o cmd -C uwsgi | grep bar_menu_dev | head -1'
```

Expected:
- shared venv = `54c8f82d…` — **배포가 돌았는데도 운영 venv가 그대로다. 격리 성공.**
- bidbar since = `2026-07-09 12:22:09 KST`
- dev 프로세스가 `bar_menu_dev/venv/bin/uwsgi`

해시가 바뀌었다면 격리 실패다. 워크플로우에 `~/bar_menu/venv`를 가리키는 줄이 남아있는지 확인한다.

- [ ] **Step 6: dev 서빙 확인**

```bash
curl -s -o /dev/null -w "devapi: %{http_code}\n" https://devapi.bar-menu.ddnsfree.com/admin/login/
```

Expected: `200`

---

### Task 3: `deploy.yml` 수리 (휴면 커밋)

**Files:**
- Modify: `.github/workflows/deploy.yml:19-36`

**Interfaces:**
- Consumes: 없음
- Produces: 없음 — Phase 3(main 머지)까지 발효되지 않는다.

`deploy.yml`은 `push: branches: [main]`에서만 트리거된다. develop에 커밋해도 실행되지 않는다. 또한 이 파일은 `deploy-develop.yml`의 트리거 경로(`backend/**`, `.github/workflows/deploy-develop.yml`)에 해당하지 않으므로 **이 태스크의 push는 어떤 배포도 일으키지 않는다.**

- [ ] **Step 1: 세 개의 고장 수리**

`.github/workflows/deploy.yml`의 `with:` 블록 최종 형태:

```yaml
      with:
        host: ${{ secrets.SSH_HOST }}
        username: ${{ secrets.SSH_USER }}
        key: ${{ secrets.SSH_PRIVATE_KEY }}
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

수정 내역 다섯 가지:

1. `script_stop: true` 추가 — 중간 실패가 red로 드러난다
2. `cd backend` + `source venv/bin/activate` → `source ~/bar_menu/venv/bin/activate`. 기존 경로 `~/bar_menu/backend/venv`는 서버에 존재하지 않는다. activate가 성공하면 venv의 `python`이 PATH에 잡히므로 `python manage.py`도 함께 살아난다(서버에는 `python3`만 있고 `python`이 없어서 migrate가 한 번도 실행된 적 없었다).
3. `pip install -q -r requirements.txt` → `-r backend/requirements.txt`. `cd backend`를 없앴으므로 경로를 맞춘다. `cd menu_project` → `cd backend/menu_project`도 같은 이유.
4. `sudo systemctl restart uwsgi` → `sudo systemctl restart bidbar`. 소켓 `/home/ubuntu/bar_menu/menu_project/bar_menu.sock`을 실제 점유한 것은 `bidbar.service`(PID 3715439)로 실측 확인됐다. `uwsgi`는 emperor이며 그 vassal은 고아 상태다.
5. 마지막 `echo "✓ Backend Deployment completed successfully!"` 삭제 — 최근 8회 연속 초록불의 원인이다.

- [ ] **Step 2: 트리거 안 걸리는지 확인**

```bash
grep -A3 "^on:" .github/workflows/deploy.yml
```

Expected: `branches:` 아래 `- main`만 존재. `develop`이 없어야 한다. 있으면 이 커밋이 즉시 운영 배포를 일으킨다 — Phase 1 위반이므로 중단한다.

- [ ] **Step 3: 커밋 + push**

```bash
git add .github/workflows/deploy.yml
git commit -m "ci: fix production deploy silently doing nothing

deploy.yml failed at three points and reported success every time:

- 'cd backend && source venv/bin/activate' targeted
  ~/bar_menu/backend/venv, which does not exist
- 'python manage.py migrate' — the server has python3, not python,
  so migrate and collectstatic never ran
- restarted uwsgi (the emperor) while bidbar.service is what actually
  holds the socket, so code never reloaded

script_stop defaults to false and the script ended in a success echo,
so all 8 recent runs were green while only git reset --hard ran.

Dormant until merged to main; this workflow triggers on main only."
git push origin develop
```

- [ ] **Step 4: 배포가 안 돌았는지 확인**

```bash
sleep 20
gh run list --limit 3
```

Expected: 이 커밋으로 인한 새 workflow run이 **없다.** `deploy.yml`은 main 전용이고, `deploy-develop.yml`의 경로 필터에도 안 걸린다.

새 run이 떴다면 즉시 확인한다. 예상과 다르게 트리거된 것이다.

---

### Task 4: `uwsgi` 버전 핀 + 죽은 파일 삭제

**Files:**
- Modify: `backend/requirements.txt:12`
- Delete: `backend/Procfile`
- Delete: `backend/menu_project/uwsgi.ini`

**Interfaces:**
- Consumes: Task 2가 전환한 dev venv 배포 경로
- Produces: 최종 회귀 테스트 결과

`backend/**`를 건드리므로 **push 시 develop 배포가 실행된다.** 이것이 Phase 1의 최종 검증이다 — requirements 변경이라는 가장 위험한 시나리오에서 공유 venv가 버티는지 본다.

- [ ] **Step 1: uwsgi 핀**

`backend/requirements.txt` 마지막 줄:

```
uwsgi>=2.0.20
```

을 아래로 바꾼다:

```
uwsgi==2.0.31
```

2.0.31은 현재 서버 설치 버전이다. 핀이 없으면 배포마다 최신 uwsgi가 설치될 수 있고, 그 바이너리는 운영 `bidbar.service`의 `ExecStart`가 직접 가리키는 파일이다.

- [ ] **Step 2: 죽은 파일 삭제**

```bash
git rm backend/Procfile backend/menu_project/uwsgi.ini
```

`backend/Procfile`은 `web: gunicorn menu_project.wsgi --log-file -`인데 OCI는 uwsgi로 서빙한다. 6/20 모노레포 분리 이후 아무도 안 쓴다.

`backend/menu_project/uwsgi.ini`는 소켓을 `uwsgi.sock`, venv를 `backend/venv`로 지정하는데 실제 서비스는 `bar_menu.sock`과 `~/bar_menu/venv`를 쓴다. 진짜 설정은 서버의 `/etc/uwsgi/vassals/bar_menu.ini`다. 리포의 이 파일은 읽는 사람을 틀린 방향으로 안내한다.

- [ ] **Step 3: 배포 전 기준선 재확인**

```bash
ssh -i ~/.ssh/deploy_test.key ubuntu@140.245.71.233 'echo "shared: $(~/bar_menu/venv/bin/pip freeze | sha256sum | cut -d" " -f1)"; echo "dev uwsgi: $(~/bar_menu_dev/venv/bin/uwsgi --version)"'
```

Expected: shared = `54c8f82d…`, dev uwsgi = `2.0.31`

- [ ] **Step 4: 커밋 + push — 배포 발생**

```bash
git add backend/requirements.txt
git commit -m "chore: pin uwsgi and drop dead deploy files

uwsgi was unpinned (>=2.0.20) while bidbar.service's ExecStart points
directly at ~/bar_menu/venv/bin/uwsgi. Pin to the installed 2.0.31 so a
deploy cannot swap the binary under a running production service.

Delete backend/Procfile (names gunicorn; OCI serves via uwsgi) and
backend/menu_project/uwsgi.ini (socket and venv paths do not match the
real service; the live config is /etc/uwsgi/vassals/bar_menu.ini on the
server). Both have been misleading since the 06-20 monorepo split."
git push origin develop
gh run watch $(gh run list --workflow=deploy-develop.yml --limit 1 --json databaseId --jq '.[0].databaseId')
```

Expected: workflow **green**

- [ ] **Step 5: 최종 회귀 테스트**

```bash
ssh -i ~/.ssh/deploy_test.key ubuntu@140.245.71.233 'echo "=== 격리 검증 ==="; echo "shared venv : $(~/bar_menu/venv/bin/pip freeze | sha256sum | cut -d" " -f1)"; echo "prod uwsgi  : $(~/bar_menu/venv/bin/uwsgi --version)"; echo "dev uwsgi   : $(~/bar_menu_dev/venv/bin/uwsgi --version)"; echo "bidbar since: $(systemctl show bidbar -p ActiveEnterTimestamp --value)"; echo "dev 프로세스 :"; ps -o cmd -C uwsgi | grep bar_menu_dev | head -1'
```

Expected:
- shared venv = `54c8f82d…` — **requirements.txt를 바꿔 배포했는데도 운영 venv가 불변이다. Phase 1의 목표가 달성됐다.**
- prod uwsgi = `2.0.31`, dev uwsgi = `2.0.31`
- bidbar since = `2026-07-09 12:22:09 KST`
- dev 프로세스가 `bar_menu_dev/venv/bin/uwsgi`

- [ ] **Step 6: 양쪽 서비스 최종 확인**

```bash
curl -s -o /dev/null -w "devapi: %{http_code}\n" https://devapi.bar-menu.ddnsfree.com/admin/login/
curl -s -o /dev/null -w "prod  : %{http_code}\n" https://api.bar-menu.ddnsfree.com/admin/login/
curl -s -o /dev/null -w "front : %{http_code}\n" https://bar-menu.ddnsfree.com/
```

Expected: 전부 `200`

---

## 완료 조건

Phase 1은 아래가 전부 참일 때 끝난다.

| 항목 | 기대 |
|---|---|
| 공유 venv 해시 | `54c8f82d…` (전 과정 불변) |
| `bidbar.service` 기동 시각 | `2026-07-09 12:22:09 KST` (재시작 없음) |
| dev 실행 바이너리 | `~/bar_menu_dev/venv/bin/uwsgi` |
| `deploy-develop.yml` | green, `script_stop: true` |
| `deploy.yml` | 수리 완료, main 머지까지 휴면 |
| 운영/dev/프론트 | 전부 200 |

## 후속 (이번 범위 아님)

- **Phase 2** — 고아 vassal 제거 + `bidbar` 재시작 + 죽은 `~/bar_menu/backend/.env` 격리. 운영 재시작이 필요하므로 별도 승인과 점검창이 필요하다. 브랜치와 무관하게 언제든 실행 가능.
- **Phase 3** — develop → main 머지. 수리된 `deploy.yml`이 처음 발효되며 `seed_from_prod.py`와 `settings.py`의 `DB_NAME` fail-fast가 운영에 반영된다. 운영 `.env`에 `DB_NAME`이 있음을 확인했으므로 안전하나, 첫 실제 배포이므로 지켜봐야 한다.
- 메모리 갱신 — `uwsgi_service_duplication.md`의 "deploy.yml이 엉뚱한 서비스를 재시작" 항목이 Phase 3 이후 해소된다. `develop_staging_environment.md`의 "운영 venv `~/bar_menu/venv` 재사용" 서술은 Task 1 완료 시점에 사실이 아니게 된다.
