// ================================================================
// FWS 프론트엔드 환경 설정
// ★ IP를 바꿀 때는 이 파일만 수정하면 됩니다 ★
// main.js / provision.js 두 파일 모두 이 설정을 공유합니다.
// ================================================================

// 로컬 테스트 (백엔드를 같은 PC에서 실행할 때)
// const BACKEND_URL   = 'http://localhost:8000';
// const GUACAMOLE_URL = 'http://localhost:8080';

// 실제 서버 배포
const BACKEND_URL   = 'http://192.168.0.36:8000';   // Service-Server
const GUACAMOLE_URL = 'http://192.168.0.38:8080';   // Guacamole VM
