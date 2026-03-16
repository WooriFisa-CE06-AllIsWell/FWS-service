# FWS — VM 온디맨드 프로비저닝 플랫폼

> VMware vSphere 환경에서 웹 UI 한 번으로 VM을 생성하고, 브라우저에서 바로 SSH 접속까지 가능한 셀프서비스 인프라 플랫폼

---

## 주요 기능

| 기능 | 설명 |
|------|------|
| VM 생성 | OS(Ubuntu/Rocky Linux), CPU/MEM/DISK 선택 후 자동 클론 |
| VM 반납 | 버튼 한 번으로 VM 삭제 및 자원 반환 |
| 자원 현황 | 클러스터 CPU/MEM/Storage 실시간 사용률 표시 |
| 웹 터미널 | VM 생성 즉시 Guacamole SSH 연결 자동 등록 및 접속 URL 제공 |
| 다크/라이트 테마 | 로컬스토리지 기반 테마 유지 |

---

## 기술 스택

| 영역 | 기술 |
|------|------|
| Backend | Python, FastAPI, uvicorn |
| VM 제어 | pyVmomi (VMware vSphere SOAP API) |
| 웹 터미널 | Apache Guacamole REST API |
| Frontend | HTML/CSS/JavaScript (Vanilla) |
| 인프라 | VMware vSphere 7.0, RHEL 9, Docker, nginx |

---

## 아키텍처

```
[사용자 브라우저]
      │
      ▼
[FWS Frontend]  nginx  ──→  [FWS Backend]  FastAPI
                                    │               │
                                    ▼               ▼
                             [vCenter SOAP]   [Guacamole REST]
                                    │               │
                                    ▼               ▼
                             [VM 생성/삭제]    [SSH 웹 터미널]
```

**Service-Server** (NIC 2개)가 핵심: 사용자망(192.168.x.x)과 vCenter 내부망(172.18.x.x)을 동시에 연결하여 백엔드가 양쪽 모두 접근 가능.

---

## 프로젝트 구조

```
FWS/
├── FWS-server/              # FastAPI 백엔드
│   ├── main.py              # 앱 진입점, CORS 설정
│   ├── config.py            # 환경변수 로딩
│   ├── routers/
│   │   ├── vm.py            # VM 생성/삭제/접속 API
│   │   └── resources.py     # 클러스터 자원 현황 API
│   ├── services/
│   │   ├── vcenter.py       # pyVmomi SOAP API 연동
│   │   └── guacamole.py     # Guacamole REST API 연동
│   ├── .env.example
│   └── requirements.txt
└── FWS-web/                 # 정적 프론트엔드
    ├── index.html
    ├── provision.html
    └── js/
        ├── config.js        # URL 설정 (★ IP 변경 시 여기만)
        ├── main.js
        └── provision.js
```

---

## API

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/health` | 서버 상태 확인 |
| GET | `/api/resources` | 클러스터 자원 현황 |
| POST | `/api/vm/create` | VM 생성 |
| POST | `/api/vm/delete` | VM 반납 |
| GET | `/api/vm/connect?vm_name=xxx` | Guacamole 접속 URL 조회 |

---

## 배포 (RHEL 9 기준)

```bash
# 패키지 설치
dnf install -y git python3 python3-pip nginx

# 클론 및 설정
git clone https://github.com/WooriFisa-CE06-AllIsWell/FWS-service.git
cp FWS-service/FWS-server/.env.example FWS-service/FWS-server/.env
vi FWS-service/FWS-server/.env

# 백엔드 실행
cd FWS-service/FWS-server
pip3 install -r requirements.txt
nohup python3 main.py > ~/fws-backend.log 2>&1 &

# 프론트엔드 (nginx)
cp -r FWS-service/FWS-web/* /usr/share/nginx/html/
systemctl enable --now nginx

# 방화벽
firewall-cmd --add-port=8000/tcp --add-port=80/tcp --permanent
firewall-cmd --reload
```

---

## 환경변수

`.env.example` 복사 후 실제 값으로 수정:

```env
MOCK_MODE=false

VCENTER_HOST=<vCenter IP>
VCENTER_USER=administrator@vcenter.<도메인>.vcsa
VCENTER_PASSWORD=<비밀번호>
VCENTER_VERIFY_SSL=false

TEMPLATE_UBUNTU=vm-XX    # MoRef ID
TEMPLATE_ROCKY=vm-XX

CLUSTER=domain-cXX
DATASTORE=datastore-XX
VM_FOLDER=group-vXX

GUACAMOLE_URL=http://<Guacamole IP>:8080
GUACAMOLE_USER=guacadmin
GUACAMOLE_PASSWORD=<비밀번호>

VM_SSH_PASSWORD=<VM 기본 SSH 비밀번호>

CORS_ORIGINS=*
```

> `MOCK_MODE=true` 설정 시 vCenter/Guacamole 없이 더미 데이터로 동작 (개발/테스트용)

---

## 팀

FISA 6기 · 네 얼간이팀
