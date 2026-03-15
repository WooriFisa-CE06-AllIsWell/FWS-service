// ── 테마 토글 ──────────────────────────────────
function toggleTheme() {
  const isDark = document.documentElement.classList.toggle('dark');
  localStorage.setItem('fws-theme', isDark ? 'dark' : 'light');
  _updateBtn();
}

function _updateBtn() {
  const isDark = document.documentElement.classList.contains('dark');
  const btn = document.getElementById('theme-toggle');
  if (btn) btn.textContent = isDark ? '☀' : '🌙';
}

document.addEventListener('DOMContentLoaded', _updateBtn);
