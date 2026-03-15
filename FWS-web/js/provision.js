// ── URL 설정은 js/config.js 에서 관리합니다 ───
// BACKEND_URL, GUACAMOLE_URL 변수는 config.js 에서 선언됩니다.

// ── 상태 ──────────────────────────────────────
let selected = { os: null, cpu: null, mem: null, sto: null };
let createdVM = null;  // 생성된 VM 정보 저장

// ── 시계 ──────────────────────────────────────
function updateClock() {
  const el = document.getElementById('clock');
  if (!el) return;
  const now = new Date();
  el.textContent = now.toLocaleTimeString('ko-KR', { hour12: false });
}
setInterval(updateClock, 1000);
updateClock();

// ── 가용 자원 불러오기 (백엔드 연동) ──────────
async function loadResources() {
  try {
    const res = await fetch(`${BACKEND_URL}/api/resources`);
    const data = await res.json();

    // CPU
    const cpuPct = Math.round((data.cpu_used / data.cpu_total) * 100);
    document.getElementById('cpu-bar').style.width = `${cpuPct}%`;
    document.getElementById('cpu-val').innerHTML =
      `사용 가능: <span class="highlight">${data.cpu_available} vCPU</span>`;

    // 메모리
    const memPct = Math.round((data.mem_used / data.mem_total) * 100);
    document.getElementById('mem-bar').style.width = `${memPct}%`;
    document.getElementById('mem-val').innerHTML =
      `사용 가능: <span class="highlight">${data.mem_available} GB</span>`;

    // 스토리지
    const stoPct = Math.round((data.sto_used / data.sto_total) * 100);
    document.getElementById('sto-bar').style.width = `${stoPct}%`;
    document.getElementById('sto-val').innerHTML =
      `사용 가능: <span class="highlight">${data.sto_available} GB</span>`;

  } catch (e) {
    // 백엔드 연결 전 더미 데이터로 표시
    console.log('백엔드 미연결 - 더미 데이터 표시');
  }
}

loadResources();

// ── OS 선택 ───────────────────────────────────
function selectOS(el) {
  document.querySelectorAll('.os-card').forEach(c => c.classList.remove('selected'));
  el.classList.add('selected');
  selected.os = el.dataset.os;
  updateSummary();
}

// ── 스펙 선택 ─────────────────────────────────
function selectSpec(el) {
  const type = el.dataset.type;
  document.querySelectorAll(`.spec-btn[data-type="${type}"]`)
    .forEach(b => b.classList.remove('selected'));
  el.classList.add('selected');
  selected[type] = el.dataset.val;
  updateSummary();
}

// ── 선택 요약 업데이트 ─────────────────────────
function updateSummary() {
  const { os, cpu, mem, sto } = selected;
  const btn = document.getElementById('create-btn');
  const txt = document.getElementById('summary-text');

  if (os && cpu && mem && sto) {
    const osLabel = os === 'ubuntu' ? 'Ubuntu 22.04' : 'Rocky Linux 9';
    txt.innerHTML =
      `<span class="highlight">${osLabel}</span> · CPU ${cpu}core · MEM ${mem}GB · DISK ${sto}GB`;
    btn.disabled = false;
  } else {
    txt.textContent = 'OS / CPU / MEM / STORAGE 를 선택하세요';
    btn.disabled = true;
  }
}

// ── VM 생성 ───────────────────────────────────
async function createVM() {
  const btn = document.getElementById('create-btn');
  const originalText = btn.textContent;
  btn.disabled = true;
  btn.textContent = '생성 중...';

  try {
    const res = await fetch(`${BACKEND_URL}/api/vm/create`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        os:      selected.os,
        cpu:     parseInt(selected.cpu),
        memory:  parseInt(selected.mem),
        storage: parseInt(selected.sto),
      })
    });

    const data = await res.json();

    if (res.ok) {
      createdVM = data;
      showResult(data);
      showToast(`✓ ${data.vm_name} 생성 완료!`);
    } else {
      // FastAPI 오류는 detail 필드로 반환됨
      const errMsg = data.detail || data.message || '생성 실패';
      showToast(`✗ 오류: ${typeof errMsg === 'string' ? errMsg : JSON.stringify(errMsg)}`, true);
      btn.disabled = false;
      btn.textContent = originalText;
    }

  } catch (e) {
    // 백엔드 미연결 시 더미 데이터로 UI 테스트
    const dummy = {
      vm_name:   'fws-vm-001',
      ip:        '192.168.11.50',
      os:        selected.os === 'ubuntu' ? 'Ubuntu 22.04 LTS' : 'Rocky Linux 9',
      cpu:       selected.cpu,
      memory:    selected.mem,
      storage:   selected.sto,
      ssh_user:  selected.os === 'ubuntu' ? 'ubuntu' : 'rocky',
    };
    createdVM = dummy;
    showResult(dummy);
    showToast(`✓ ${dummy.vm_name} 생성 완료! (더미)`)
    btn.disabled = false;
    btn.textContent = originalText;
  }
}

// ── 결과 표시 ─────────────────────────────────
function showResult(data) {
  const ssh = `ssh ${data.ssh_user}@${data.ip}`;

  document.getElementById('res-name').textContent = data.vm_name;
  document.getElementById('res-ip').textContent   = data.ip;
  document.getElementById('res-os').textContent   = data.os;
  document.getElementById('res-spec').textContent =
    `CPU ${data.cpu}core / MEM ${data.memory}GB / DISK ${data.storage}GB`;
  document.getElementById('res-ssh').textContent  = ssh;

  const section = document.getElementById('result-section');
  section.style.display = 'block';
  section.scrollIntoView({ behavior: 'smooth', block: 'start' });

  // 반납 입력창에 VM 이름 자동 입력
  document.getElementById('return-vm-name').value = data.vm_name;
}

// ── SSH 명령어 복사 ───────────────────────────
function copySSH() {
  if (!createdVM) return;
  const ssh = `ssh ${createdVM.ssh_user}@${createdVM.ip}`;
  navigator.clipboard.writeText(ssh)
    .then(() => showToast('✓ 복사 완료'))
    .catch(() => showToast('✗ 복사 실패', true));
}

// ── Guacamole 접속 ────────────────────────────
function goGuacamole() {
  // 백엔드가 VM 생성 시 등록한 직접 접속 URL 사용 (없으면 Guacamole 홈으로)
  const url = createdVM?.guacamole_url || `${GUACAMOLE_URL}/guacamole/`;
  window.open(url, '_blank');
}

// ── VM 반납 ───────────────────────────────────
async function returnVM() {
  const vmName = document.getElementById('return-vm-name').value.trim();
  if (!vmName) {
    showToast('✗ VM 이름을 입력하세요', true);
    return;
  }

  if (!confirm(`"${vmName}" 을 반납하시겠습니까?\n모든 데이터가 삭제됩니다.`)) return;

  try {
    const res = await fetch(`${BACKEND_URL}/api/vm/delete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ vm_name: vmName })
    });

    const data = await res.json();

    if (res.ok) {
      showToast(`✓ ${vmName} 반납 완료`);
      document.getElementById('return-vm-name').value = '';
      // 결과 섹션 숨기기
      document.getElementById('result-section').style.display = 'none';
      loadResources();  // 자원 현황 갱신
    } else {
      const errMsg = data.detail || data.message || '반납 실패';
      showToast(`✗ ${typeof errMsg === 'string' ? errMsg : JSON.stringify(errMsg)}`, true);
    }

  } catch (e) {
    // 백엔드 미연결 시
    showToast(`✓ ${vmName} 반납 완료 (더미)`);
    document.getElementById('return-vm-name').value = '';
    document.getElementById('result-section').style.display = 'none';
  }
}

// ── 토스트 알림 ───────────────────────────────
function showToast(msg, isError = false) {
  const toast = document.getElementById('toast');
  toast.textContent = msg;
  toast.classList.toggle('error', isError);
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 3000);
}
