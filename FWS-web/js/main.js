// ── URL 설정은 js/config.js 에서 관리합니다 ───
// BACKEND_URL, GUACAMOLE_URL 변수는 config.js 에서 선언됩니다.

// ── 시계 ──────────────────────────────────────
function updateClock() {
  const el = document.getElementById('clock');
  if (!el) return;
  const now = new Date();
  el.textContent = now.toLocaleTimeString('ko-KR', { hour12: false });
}
setInterval(updateClock, 1000);
updateClock();

// ── 접속하기 버튼 → 모달 열기 ─────────────────
document.getElementById('btn-connect').addEventListener('click', (e) => {
  e.preventDefault();
  document.getElementById('connect-modal').classList.add('active');
  document.getElementById('vm-name-connect').focus();
});

// ── 모달 닫기 ─────────────────────────────────
function closeModal() {
  document.getElementById('connect-modal').classList.remove('active');
}

// 모달 바깥 클릭 시 닫기
document.getElementById('connect-modal').addEventListener('click', (e) => {
  if (e.target === e.currentTarget) closeModal();
});

// ── Guacamole로 이동 ───────────────────────────
async function connectGuacamole() {
  const vmName = document.getElementById('vm-name-connect').value.trim();
  if (!vmName) {
    alert('VM 이름을 입력하세요.');
    return;
  }
  closeModal();

  // 백엔드에 VM 이름으로 Guacamole 직접 접속 URL 조회
  try {
    const res = await fetch(`${BACKEND_URL}/api/vm/connect?vm_name=${encodeURIComponent(vmName)}`);
    if (res.ok) {
      const data = await res.json();
      window.open(data.guacamole_url, '_blank');
      return;
    }
  } catch (e) {
    // 백엔드 미연결 시 Guacamole 홈으로 이동
  }
  window.open(`${GUACAMOLE_URL}/guacamole/`, '_blank');
}
