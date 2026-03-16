# FWS 포트폴리오 요약

> 이력서/포트폴리오 사이트용 프로젝트 설명 초안입니다.

---

## 한 줄 요약

VMware vSphere 환경에서 웹 UI로 VM을 온디맨드 프로비저닝하고, 브라우저에서 즉시 SSH 접속 가능한 셀프서비스 인프라 플랫폼 개발

---

## 프로젝트 개요

| 항목 | 내용 |
|------|------|
| 기간 | 2026.03 |
| 인원 | 4인 팀 프로젝트 |
| 역할 | 백엔드 API 설계 및 구현, 인프라 연동, 배포 전 과정 |
| GitHub | https://github.com/WooriFisa-CE06-AllIsWell/FWS-service |

---

## 기술 스택

- **Backend**: Python, FastAPI
- **VM 제어**: pyVmomi (VMware vSphere SOAP API)
- **웹 터미널**: Apache Guacamole REST API
- **Frontend**: HTML/CSS/Vanilla JS
- **인프라**: VMware vSphere 7.0, RHEL 9, Docker, nginx

---

## 핵심 구현 내용

### 1. VM 자동 프로비저닝
- FastAPI 백엔드에서 vSphere SOAP API(pyVmomi)로 VM 클론 자동화
- OS, CPU, 메모리, 디스크를 파라미터로 받아 지정 클러스터/데이터스토어에 배포
- VM 파워온 후 IP 할당까지 대기하는 폴링 로직 구현 (최대 5분 타임아웃)

### 2. Guacamole 연동으로 웹 터미널 자동 제공
- VM 생성 완료 시 Guacamole REST API로 SSH 연결 자동 등록
- Base64 인코딩된 직접 접속 URL 생성 → 사용자가 버튼 클릭 한 번으로 웹 SSH 접속
- VM 반납 시 Guacamole 연결도 함께 자동 삭제

### 3. 듀얼 NIC 네트워크 설계
- Service-Server에 NIC 2개 구성: 사용자망(192.168.x.x) + vCenter 내부망(172.18.x.x)
- 브라우저 → 백엔드(사용자망), 백엔드 → vCenter/VM(내부망) 분리로 보안 및 연결성 확보

### 4. 환경변수 기반 설정 관리
- vCenter, Guacamole, VM 템플릿 정보를 모두 `.env`로 분리
- `MOCK_MODE` 플래그로 실제 인프라 없이 더미 데이터로 개발/테스트 가능

---

## 주요 트러블슈팅

### vSphere 7.0.3 REST API 미지원 → pyVmomi로 전환
- vSphere 7.0.3에서 `POST /api/vcenter/vm?action=clone` 미지원(404) 확인
- VMware 공식 Python 라이브러리인 pyVmomi의 SOAP API(`CloneVM_Task`)로 전환
- REST API는 자원 조회에만 사용, VM 생성/삭제는 SOAP API로 처리하는 하이브리드 구조 채택

### Guacamole 파일 인증 → MySQL DB 인증 전환
- 기존 파일 기반 인증(`user-mapping.xml`)은 REST API로 연결 동적 생성 불가(PERMISSION_DENIED)
- docker-compose에 MySQL 컨테이너 추가, DB 기반 인증으로 전환하여 REST API 완전 활성화

### vSphere REST API 필터 파라미터 호환성
- `filter.power_states`, `filter.names` 쿼리 파라미터가 vSphere 7.0.3에서 400 오류 발생
- 전체 목록 조회 후 Python 레벨에서 필터링하는 방식으로 우회

---

## 결과

- 웹 UI에서 OS/스펙 선택 → VM 생성(약 3~5분) → 웹 터미널 즉시 접속 전 과정 자동화
- Ubuntu / Rocky Linux 두 OS 템플릿 지원
- MOCK_MODE로 인프라 없이도 UI/API 독립 테스트 가능한 구조
