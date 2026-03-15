# FWS Backend

VMware vSphere 기반 VM 온디맨드 프로비저닝 API 서버
FastAPI + vCenter REST API + Guacamole REST API

---

## 디렉토리 구조

```
FWS-server/
├── main.py                 # FastAPI 앱 진입점, CORS 설정
├── config.py               # 환경변수 로딩 (Settings 클래스)
├── routers/
│   ├── vm.py               # POST /api/vm/create, /vm/delete, GET /vm/connect
│   └── resources.py        # GET /api/resources
├── services/
│   ├── vcenter.py          # vCenter REST API 연동 로직
│   └── guacamole.py        # Guacamole REST API 연동 로직
├── .env                    # 환경변수 (★ IP·비밀번호 여기서 설정)
├── requirements.txt
└── Dockerfile
```

---

## 빠른 시작

### 1. 의존성 설치

```bash
cd FWS-server
pip install -r requirements.txt
```

### 2. 서버 실행 (개발 모드)

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. API 문서 확인

브라우저에서 열기: `http://localhost:8000/docs`
Swagger UI에서 모든 API를 직접 테스트할 수 있습니다.

### 4. Docker로 실행

```bash
docker build -t fws-server .
docker run -p 8000:8000 --env-file .env fws-server
```

---

## API 목록

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/health` | 서버 상태 확인 |
| GET | `/api/resources` | 클러스터 CPU/MEM/Storage 현황 |
| POST | `/api/vm/create` | VM 생성 |
| POST | `/api/vm/delete` | VM 반납(삭제) |
| GET | `/api/vm/connect?vm_name=xxx` | VM Guacamole 접속 URL 조회 |

### 요청/응답 예시

**GET /api/resources**
```json
{
  "cpu_total": 32, "cpu_used": 12, "cpu_available": 20,
  "mem_total": 64, "mem_used": 24, "mem_available": 40,
  "sto_total": 2000, "sto_used": 600, "sto_available": 1400
}
```

**POST /api/vm/create**
```json
// 요청
{ "os": "ubuntu", "cpu": 2, "memory": 4, "storage": 40 }

// 응답
{
  "vm_name": "fws-vm-0315-143022",
  "vm_id": "vm-123",
  "ip": "172.18.1.50",
  "os": "Ubuntu 22.04 LTS",
  "cpu": 2, "memory": 4, "storage": 40,
  "ssh_user": "ubuntu",
  "guacamole_url": "http://192.168.11.YYY:8080/guacamole/#/client/..."
}
```

**POST /api/vm/delete**
```json
// 요청
{ "vm_name": "fws-vm-0315-143022" }

// 응답
{ "success": true, "message": "fws-vm-0315-143022 반납 완료" }
```

---

## 환경 설정 (.env)

> `.env` 파일을 열어 각 항목을 환경에 맞게 수정하세요.

### MOCK 모드 vs 실제 모드

```
# 개발/테스트: vCenter 없이 더미 데이터 반환
MOCK_MODE=true

# 실제 운영: vCenter, Guacamole 실제 API 호출
MOCK_MODE=false
```

### MOCK_MODE=true 일 때

- vCenter, Guacamole에 아무것도 연결하지 않아도 됩니다
- 모든 API가 즉시 더미 데이터를 반환합니다
- VM 생성 응답: `ip=192.168.11.50`, `vm_name=fws-vm-MMDD-HHmmss` (타임스탬프)
- Guacamole URL은 Guacamole 홈 주소로 반환됩니다

### MOCK_MODE=false 일 때 반드시 설정해야 하는 항목

```env
VCENTER_PASSWORD=실제_비밀번호

# 템플릿 이름: vCenter UI에서 정확히 확인
TEMPLATE_UBUNTU=ubuntu-22.04-template
TEMPLATE_ROCKY=rocky-linux-9-template

# MoRef ID: vCenter MOB 또는 아래 API로 확인
# curl -sk -u admin:pass https://vcenter/api/vcenter/cluster
CLUSTER=domain-c8
DATASTORE=datastore-10
VM_FOLDER=group-v100

GUACAMOLE_URL=http://192.168.11.YYY:8080
GUACAMOLE_PASSWORD=실제_비밀번호
```

### MoRef ID 확인 방법

```bash
# vCenter 로그인
curl -sk -X POST https://172.18.0.10/api/session \
  -u "administrator@vsphere.local:비밀번호" | tr -d '"'
# → 세션 토큰 출력

# 클러스터 ID 확인 (domain-cXX 형태)
curl -sk https://172.18.0.10/api/vcenter/cluster \
  -H "vmware-api-session-id: 세션토큰"

# 데이터스토어 ID 확인
curl -sk https://172.18.0.10/api/vcenter/datastore \
  -H "vmware-api-session-id: 세션토큰"

# 폴더 ID 확인
curl -sk https://172.18.0.10/api/vcenter/folder \
  -H "vmware-api-session-id: 세션토큰"
```

---

## 코드에서 수정할 부분

### 목 데이터 변경

`services/vcenter.py` 맨 아래 `get_mock_resources()`, `get_mock_vm()` 함수:

```python
def get_mock_resources() -> dict:
    return {
        "cpu_total": 32,    # ← 여기 값 수정
        "cpu_used": 12,
        ...
    }

def get_mock_vm(...) -> dict:
    return {
        "vm_name": f"fws-vm-{ts}",
        "ip": "192.168.11.50",   # ← 더미 IP 수정
        ...
    }
```

### vCenter 클론 스펙 수정

`services/vcenter.py` → `create_vm()` 내 `clone_spec` 딕셔너리:

```python
clone_spec = {
    "name": vm_name,
    "source": template_id,
    "placement": {
        "cluster":   settings.CLUSTER,    # .env에서 관리
        "datastore": settings.DATASTORE,
        "folder":    settings.VM_FOLDER,
    },
    "hardware_customization": { ... }
}
```

### Guacamole SSH 비밀번호 설정

`services/guacamole.py` → `create_ssh_connection()` 내 parameters:

```python
"parameters": {
    "hostname": ip,
    "port": "22",
    "username": ssh_user,
    # "password": "vm-default-password",  # ← 주석 해제 후 비밀번호 입력
    # 또는 키 기반 인증 사용 시 "private-key": "..." 설정
},
```

---

## 네트워크 구성

```
[사용자 PC]  192.168.11.x
      │
      ├──→ [프론트/백 VM]    NIC1: 192.168.11.A:8000  (사용자 접근)
      │                      NIC2: 172.18.0.x          (vCenter, VM 내부망)
      │
      └──→ [Guacamole VM]   NIC1: 192.168.11.B:8080  (사용자 브라우저)
                             NIC2: 172.18.0.x          (신규 VM에 SSH)

[vCenter / 신규 VM들]  172.18.0.0/20  (내부망 전용)
```

`GUACAMOLE_URL`에는 사용자 브라우저가 접근 가능한 `192.168.11.B:8080` 을 넣어야 합니다.
백엔드도 동일한 주소로 Guacamole API를 호출하고, 생성된 접속 URL도 그 주소 기반으로 만들어집니다.
