# FWS Frontend

VMware vSphere VM 셀프서비스 포털 — 프론트엔드
순수 HTML/CSS/JavaScript (빌드 도구 없음, 파일 그대로 열거나 웹서버로 서빙)

---

## 디렉토리 구조

```
FWS-web/
├── index.html          # 홈 화면 (VM 생성/반납 이동, VM 접속 모달)
├── provision.html      # VM 생성 · 반납 화면
├── css/
│   └── style.css       # 전체 스타일
└── js/
    ├── config.js       # ★ URL 설정 (이 파일만 수정하면 됨)
    ├── theme.js        # 다크/라이트 모드 토글
    ├── main.js         # index.html 로직
    └── provision.js    # provision.html 로직 (API 호출 포함)
```

---

## IP 설정 방법

> **`js/config.js` 파일 하나만 수정하면 됩니다.**
> `main.js`, `provision.js`는 건드릴 필요 없습니다.

```js
// js/config.js

// 로컬 테스트 (백엔드를 같은 PC에서 실행)
const BACKEND_URL   = 'http://localhost:8000';
const GUACAMOLE_URL = 'http://localhost:8080';

// 실제 서버 배포 시 ↓ 주석 해제, ↑ 주석 처리
// const BACKEND_URL   = 'http://192.168.11.XXX:8000';   // 백엔드 VM IP
// const GUACAMOLE_URL = 'http://192.168.11.YYY:8080';   // Guacamole VM IP
```

---

## 실행 방법

### 방법 1: 파일 직접 열기 (가장 간단)

`index.html`을 브라우저로 열면 됩니다.
단, 백엔드가 `localhost:8000`에 실행 중이어야 API가 작동합니다.
백엔드 없이도 더미 데이터로 UI 동작 확인은 가능합니다.

### 방법 2: 간단한 HTTP 서버 (Python)

```bash
cd FWS-web
python -m http.server 3000
# 브라우저에서 http://localhost:3000 접속
```

### 방법 3: VS Code Live Server 확장

VS Code에서 `index.html` 우클릭 → "Open with Live Server"

---

## 화면 구성

### index.html (홈)

- `[생성 / 반납]` 버튼 → `provision.html` 이동
- `[VM 접속]` 버튼 → VM 이름 입력 모달 → 백엔드에 Guacamole URL 조회 → 새 탭 열기

### provision.html (VM 생성/반납)

1. **자원 현황** — `GET /api/resources` 호출해서 CPU/MEM/Storage 사용률 표시
2. **VM 생성** — OS/CPU/메모리/스토리지 선택 후 `POST /api/vm/create`
   - 완료 시 VM 이름, IP, SSH 명령어, "웹 터미널 접속" 버튼 표시
   - "웹 터미널 접속" 버튼 클릭 → Guacamole 해당 VM SSH 터미널로 직접 이동
3. **VM 반납** — VM 이름 입력 후 `POST /api/vm/delete`

---

## 백엔드 없이 테스트 (더미 모드)

백엔드 서버가 없거나 응답이 없으면 자동으로 더미 데이터로 동작합니다.

| 기능 | 백엔드 없을 때 동작 |
|------|---------------------|
| 자원 현황 | 하드코딩된 막대 그래프 그대로 표시 |
| VM 생성 | `fws-vm-001 / 192.168.11.50` 더미 데이터 표시 |
| VM 반납 | 성공 toast 표시 (실제 삭제 없음) |
| VM 접속 | Guacamole 홈으로 이동 |

더미 데이터 내용을 바꾸려면 `js/provision.js`의 `createVM()` 함수 내 `catch` 블록:

```js
// js/provision.js - createVM() - catch 블록
const dummy = {
  vm_name:  'fws-vm-001',       // ← 더미 VM 이름
  ip:       '192.168.11.50',    // ← 더미 IP
  os:       '...',
  cpu:      selected.cpu,
  memory:   selected.mem,
  storage:  selected.sto,
  ssh_user: '...',
  guacamole_url: undefined,     // 없으면 Guacamole 홈으로 이동
};
```

---

## API 연동 코드 위치

### 자원 현황 조회

`js/provision.js` → `loadResources()` 함수 (페이지 로드 시 자동 호출)

```js
const res = await fetch(`${BACKEND_URL}/api/resources`);
```

### VM 생성

`js/provision.js` → `createVM()` 함수

```js
const res = await fetch(`${BACKEND_URL}/api/vm/create`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ os, cpu, memory, storage })
});
```

### VM 반납

`js/provision.js` → `returnVM()` 함수

```js
const res = await fetch(`${BACKEND_URL}/api/vm/delete`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ vm_name: vmName })
});
```

### Guacamole 직접 접속 URL 조회 (홈 화면)

`js/main.js` → `connectGuacamole()` 함수

```js
const res = await fetch(`${BACKEND_URL}/api/vm/connect?vm_name=${vmName}`);
```

---

## 배포 체크리스트

- [ ] `js/config.js` — `BACKEND_URL`, `GUACAMOLE_URL` 실제 IP로 변경
- [ ] 백엔드 서버 실행 확인 (`http://백엔드IP:8000/health`)
- [ ] CORS 확인 — 백엔드 `.env`의 `CORS_ORIGINS`에 프론트 주소 포함 여부
- [ ] Guacamole 실행 확인 (`http://Guacamole IP:8080/guacamole`)
