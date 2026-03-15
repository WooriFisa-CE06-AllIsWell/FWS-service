# FWS — Four Guys Web Service

VMware vSphere 기반 VM 온디맨드 프로비저닝 플랫폼.
사용자가 웹 UI에서 OS/스펙을 선택하면 VM이 자동 생성되고, Guacamole 웹 터미널로 바로 접속할 수 있습니다.

---

## 아키텍처

```
[사용자 브라우저]
      │
      ▼
[FWS 프론트엔드]  http://<SERVICE_SERVER_IP>  (nginx)
      │
      ▼
[FWS 백엔드]     http://<SERVICE_SERVER_IP>:8000  (FastAPI + uvicorn)
      │                          │
      ▼                          ▼
[vCenter]                [Guacamole :8080]
      │                          │
      ▼                          ▼
[생성된 VM]  ←────────── SSH 웹 터미널 접속
```

### 서버 구성

| 서버 | 역할 |
|------|------|
| Service-Server | FWS 백엔드 + 프론트엔드 (NIC 2개: 사용자망 + 내부망) |
| Guacamole-Server | 웹 SSH 터미널 |
| vCenter | VM 관리 |

---

## 프로젝트 구조

```
FWS/
├── FWS-server/          # FastAPI 백엔드
│   ├── main.py
│   ├── config.py
│   ├── routers/
│   │   ├── vm.py        # VM 생성/삭제/접속 API
│   │   └── resources.py # 클러스터 자원 현황 API
│   ├── services/
│   │   ├── vcenter.py   # pyVmomi SOAP API (VM 생성/삭제)
│   │   └── guacamole.py # Guacamole REST API (연결 등록/삭제)
│   ├── .env             # 환경변수 (git 제외)
│   ├── .env.example     # 환경변수 템플릿
│   └── requirements.txt
└── FWS-web/             # 정적 HTML/JS 프론트엔드
    ├── index.html       # 메인 홈
    ├── provision.html   # VM 생성/반납 페이지
    ├── css/style.css
    └── js/
        ├── config.js    # 백엔드/Guacamole URL 설정 (★ IP 변경 시 여기만)
        ├── main.js
        ├── provision.js
        └── theme.js
```

---

## 배포 방법 (Service-Server 기준)

### 1. 패키지 설치

```bash
dnf install -y git python3 python3-pip nginx
```

### 2. 프로젝트 클론

```bash
git clone https://github.com/WooriFisa-CE06-AllIsWell/FWS-service.git
cd FWS-service
```

### 3. 환경변수 설정

```bash
cp FWS-server/.env.example FWS-server/.env
vi FWS-server/.env   # 실제 값으로 수정
```

### 4. Python 패키지 설치

```bash
cd FWS-server
pip3 install -r requirements.txt
```

### 5. 백엔드 실행

```bash
nohup python3 main.py > ~/fws-backend.log 2>&1 &
```

### 6. 프론트엔드 배포 (nginx)

```bash
cp -r ~/FWS-service/FWS-web/* /usr/share/nginx/html/
systemctl enable --now nginx
```

### 7. 방화벽 설정

```bash
firewall-cmd --add-port=8000/tcp --permanent
firewall-cmd --add-port=80/tcp --permanent
firewall-cmd --reload
```

---

## 환경변수 (.env)

`.env.example`을 복사해서 실제 값으로 채우세요.

```env
MOCK_MODE=false

VCENTER_HOST=<vCenter IP>
VCENTER_USER=administrator@vcenter.<도메인>.vcsa
VCENTER_PASSWORD=<비밀번호>
VCENTER_VERIFY_SSL=false

TEMPLATE_UBUNTU=vm-XX   # SSH 활성화된 Ubuntu 템플릿 MoRef ID
TEMPLATE_ROCKY=vm-XX    # Rocky Linux 템플릿 MoRef ID

CLUSTER=domain-cXX
DATASTORE=datastore-XX
VM_FOLDER=group-vXX

GUACAMOLE_URL=http://<Guacamole IP>:8080
GUACAMOLE_USER=guacadmin
GUACAMOLE_PASSWORD=<비밀번호>

VM_SSH_PASSWORD=<VM SSH 기본 비밀번호>

CORS_ORIGINS=*
```

> MoRef ID 확인: vCenter → 해당 VM/클러스터/데이터스토어 선택 → URL에서 `vm-XX`, `domain-cXX` 등 확인

---

## 작업 이력

### 기능 구현

- **VM 생성/반납**: OS(Ubuntu/Rocky), CPU/MEM/DISK 선택 후 vSphere에 자동 클론
- **자원 현황**: 클러스터 CPU/MEM/Storage 사용률 실시간 표시
- **Guacamole 자동 등록**: VM 생성 시 SSH 연결을 Guacamole에 자동 등록, 직접 접속 URL 반환
- **Guacamole 자동 삭제**: VM 반납 시 Guacamole 연결도 함께 삭제
- **다크/라이트 테마**: 로컬스토리지 기반 테마 유지

### 트러블슈팅

#### vSphere 7.0.3 API 호환성 문제

- **문제**: `POST /api/vcenter/vm?action=clone` → 404 (vSphere 7.0.3 미지원)
- **해결**: REST API 대신 **pyVmomi SOAP API**로 전환 (`SmartConnect` + `CloneVM_Task`)

#### vSphere REST API 필터 파라미터 문제

- **문제**: `filter.power_states`, `filter.names` 쿼리 파라미터 → 400 오류
- **해결**: 전체 VM 목록 조회 후 Python에서 필터링

#### VM 템플릿 MoRef ID 직접 지정

- **문제**: `/api/vcenter/vm`이 vSphere 템플릿을 반환하지 않음
- **해결**: `.env`에 MoRef ID(`vm-XX`) 직접 지정, `vm-` 접두어로 판별

#### Guacamole 파일 기반 인증 → MySQL 전환

- **문제**: 파일 기반 인증(`user-mapping.xml`)은 REST API 연결 생성 불가 (PERMISSION_DENIED)
- **해결**: docker-compose에 MySQL 컨테이너 추가, DB 기반 인증으로 전환

#### Guacamole REST API 토큰 전달 방식

- **문제**: `Guacamole-Token` 헤더 방식 → 403 오류
- **해결**: 쿼리 파라미터 `?token=TOKEN` 방식으로 변경

#### Service-Server → vCenter 네트워크 연결 불가

- **문제**: Service-Server 기존 NIC에서 vCenter 내부망 미달
- **해결**: 새 NIC 추가, 내부망 IP 할당

#### Ubuntu VM SSH 비활성화

- **문제**: Ubuntu 템플릿에 openssh-server 미설치 → SSH Connection Refused
- **해결**: 템플릿 VM에 `apt install openssh-server` 후 재템플릿화

#### Rocky Linux 네트워크 NO-CARRIER

- **문제**: Rocky 템플릿 네트워크 어댑터 미연결 → IP 미할당
- **해결**: vCenter에서 네트워크 어댑터 연결 상태 확인 및 수정

### 성능/구조 개선

- **config.js 분리**: `main.js`, `provision.js`가 공유하는 URL 설정을 `config.js` 한 파일에서 관리
- **VM_SSH_PASSWORD 환경변수화**: SSH 비밀번호를 코드 내 하드코딩 대신 `.env`로 관리
- **MoRef ID 우선 조회**: 템플릿 값이 `vm-`로 시작하면 이름 검색 없이 MoRef ID로 직접 접근

---

## Guacamole 설정 (docker-compose)

Guacamole-Server에서 MySQL 기반으로 실행:

```yaml
services:
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_DATABASE: guacamole_db
      MYSQL_USER: guacamole
      MYSQL_PASSWORD: <비밀번호>
  guacd:
    image: guacamole/guacd
  guacamole:
    image: guacamole/guacamole
    environment:
      MYSQL_HOSTNAME: mysql
      MYSQL_DATABASE: guacamole_db
    ports:
      - "8080:8080"
```

초기 관리자 계정: `guacadmin` / `guacadmin` (최초 로그인 후 변경 권장)

---

## 팀

FISA 6기 · 네 얼간이팀
