# Bid-Menu

Bid-Menu는 매장 내 테이블에 부착된 QR 코드를 스캔하여 별도의 앱 설치 없이 메뉴를 확인하는 웹 서비스입니다.

Bidbar(https://naver.me/5ISHAhLZ)의 의뢰를 받아 제작되었습니다.

관리자는 메뉴 관리와 내부 설정에 대한 컨트롤을 admin에서 진행할 수 있습니다.

Django 기반의 백엔드와 반응형 웹 프론트엔드로 구성되며, Oracle Cloud에서 배포 중입니다.


## 데모

http://bid-menu.duckdns.org/

## 기술 스택

### Backend

* Python
* Django
* Django REST Framework

### Frontend

* HTML / CSS / JavaScript
* Bootstrap (UI 프레임워크)
* Axios (비동기 데이터 통신)

### 배포 및 인프라

* Oracle Cloud Free Tier (Ubuntu 22.04)
* Nginx + uWSGI
* systemd (uWSGI 프로세스 관리)
* Certbot (Let's Encrypt SSL)

### CI/CD

* GitHub Actions
  * Trigger: main 브랜치 push
  * SSH를 통한 서버 배포
  * 타임아웃 없는 안정적인 배포

#### 서버 설정

1. GitHub Secrets 설정:
   - `HOST`: 서버 IP 주소
   - `USERNAME`: SSH 사용자명 (ubuntu)
   - `PRIVATE_KEY`: SSH 개인키

2. 서버에서 SSH 키 설정:
```bash
# 서버에서 실행
ssh-keygen -t rsa -b 4096 -C "github-actions"
cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys
# ~/.ssh/id_rsa 내용을 GitHub Secrets의 PRIVATE_KEY에 추가
```

#### GitHub Actions 장점

- 웹훅 타임아웃 문제 해결
- 배포 로그를 GitHub에서 확인 가능
- 실패 시 자동 알림
- 더 안정적이고 관리하기 쉬운 CI/CD
  

## 주요 기능

- QR 코드 기반 접속: 테이블별 고유 QR 스캔 시 해당 테이블 정보로 자동 접속
- 메뉴 조회: 카테고리별 메뉴 탐색
- 관리자 대시보드: 테이블 및 메뉴(이미지 포함) 관리, QR 코드 생성 및 다운로드
- 반응형 웹 디자인: 모바일 및 태블릿 환경에 최적화된 UI

## 프로젝트 구조

```bash
bid-menu/
├── config/                   # Django 프로젝트 설정 (settings, urls)
├── store/                    # 상점, 메뉴, 테이블 관리 앱
│   ├── models.py             # Category, Menu, Table 모델
│   ├── views.py              # 메뉴판 및 관리자 뷰
│   ├── urls.py
│   └── utils/
│       └── qr_generator.py   # QR 코드 생성 로직
├── static/                   # 정적 파일 (CSS, JS, Fonts)
├── media/                    # 업로드된 메뉴 이미지 및 생성된 QR
│   ├── menu_images/
│   └── qr_codes/
├── templates/                # 프론트엔드 HTML 템플릿
│   ├── base.html
│   ├── menu_list.html
│   ├── admin.html
├── uwsgi.ini                 # uWSGI 설정
└── requirements.txt
