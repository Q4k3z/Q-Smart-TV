// Q Smart TV - Launcher Logic
const urlParams = new URLSearchParams(window.location.search);
const token = urlParams.get('token') || localStorage.getItem('qsmart_token') || '';
if (token) localStorage.setItem('qsmart_token', token);

function getHeaders() {
  const h = { 'Content-Type': 'application/json' };
  if (token) h['Authorization'] = `Bearer ${token}`;
  return h;
}

// Clock & Date
function updateClock() {
  const now = new Date();
  const timeStr = now.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
  const dateStr = now.toLocaleDateString('vi-VN', { weekday: 'long', day: '2-digit', month: '2-digit', year: 'numeric' });
  document.getElementById('time-display').textContent = timeStr;
  document.getElementById('date-display').textContent = dateStr;
}
setInterval(updateClock, 1000);
updateClock();

// Fetch System Info & QR
async function fetchSystemInfo() {
  try {
    const res = await fetch(`/api/info`);
    if (res.ok) {
      const data = await res.json();
      document.getElementById('remote-ip-info').textContent = `IP: ${data.lan_ip} | Q Remote sẵn sàng`;
      document.getElementById('qr-image').src = `/api/qrcode?token=${token}`;
      document.getElementById('qr-url-display').textContent = data.remote_url;
    } else {
      document.getElementById('remote-ip-info').textContent = 'Chưa xác thực';
    }
  } catch (err) {
    document.getElementById('remote-ip-info').textContent = 'Server Offline';
  }
}
fetchSystemInfo();

// Spatial Keyboard Navigation
function getFocusableElements() {
  const exitModal = document.getElementById('exit-modal');
  if (exitModal.classList.contains('active')) {
    return Array.from(exitModal.querySelectorAll('.focusable'));
  }
  const qrModal = document.getElementById('qr-modal');
  if (qrModal.classList.contains('active')) {
    return Array.from(qrModal.querySelectorAll('.focusable'));
  }
  return Array.from(document.querySelectorAll('.focusable:not(.modal-overlay .focusable)'))
    .filter(el => el.offsetParent !== null);
}

function handleKeyDown(e) {
  const focusables = getFocusableElements();
  if (!focusables.length) return;

  const current = document.activeElement;
  let currentIndex = focusables.indexOf(current);
  if (currentIndex === -1) {
    focusables[0].focus();
    return;
  }

  if (e.key === 'ArrowRight') {
    e.preventDefault();
    const next = focusables[(currentIndex + 1) % focusables.length];
    next.focus();
  } else if (e.key === 'ArrowLeft') {
    e.preventDefault();
    const prev = focusables[(currentIndex - 1 + focusables.length) % focusables.length];
    prev.focus();
  } else if (e.key === 'ArrowDown') {
    e.preventDefault();
    const next = focusables[Math.min(currentIndex + 3, focusables.length - 1)];
    next.focus();
  } else if (e.key === 'ArrowUp') {
    e.preventDefault();
    const prev = focusables[Math.max(currentIndex - 3, 0)];
    prev.focus();
  } else if (e.key === 'Enter') {
    e.preventDefault();
    current.click();
  } else if (e.key === 'Escape' || e.key === 'Backspace') {
    const exitModal = document.getElementById('exit-modal');
    if (exitModal.classList.contains('active')) {
      e.preventDefault();
      closeExitModal();
      return;
    }
    const qrModal = document.getElementById('qr-modal');
    if (qrModal.classList.contains('active')) {
      e.preventDefault();
      closeQrModal();
      return;
    }
  } else if (e.key === 'Home') {
    e.preventDefault();
    closeExitModal();
    closeQrModal();
    const appGrid = document.getElementById('app-grid');
    const firstCard = appGrid.querySelector('.focusable');
    if (firstCard) firstCard.focus();
  }
}

document.addEventListener('keydown', handleKeyDown);

// Exit Modal Handling
const exitBtn = document.getElementById('exit-btn');
const exitModal = document.getElementById('exit-modal');
const btnCancelExit = document.getElementById('btn-cancel-exit');
const btnConfirmExit = document.getElementById('btn-confirm-exit');

function openExitModal() {
  exitModal.classList.add('active');
  btnCancelExit.focus();
}

function closeExitModal() {
  exitModal.classList.remove('active');
  exitBtn.focus();
}

exitBtn.addEventListener('click', openExitModal);
btnCancelExit.addEventListener('click', closeExitModal);
btnConfirmExit.addEventListener('click', async () => {
  try {
    await fetch(`/api/launcher/exit?token=${token}`, {
      method: 'POST',
      headers: getHeaders()
    });
  } catch (err) {
    console.error('Lỗi khi gửi lệnh thoát launcher:', err);
  }
});

// QR Pairing Modal
const qrPairingBtn = document.getElementById('qr-pairing-btn');
const qrModal = document.getElementById('qr-modal');
const btnCloseQr = document.getElementById('btn-close-qr');

function openQrModal() {
  qrModal.classList.add('active');
  btnCloseQr.focus();
}

function closeQrModal() {
  qrModal.classList.remove('active');
  qrPairingBtn.focus();
}

qrPairingBtn.addEventListener('click', openQrModal);
btnCloseQr.addEventListener('click', closeQrModal);

// App Launcher Actions
document.querySelectorAll('.app-card').forEach(card => {
  card.addEventListener('click', () => {
    const appType = card.dataset.app;
    handleAppClick(appType);
  });
});

async function handleAppClick(appType) {
  const container = document.getElementById('content-view');

  if (appType === 'youtube') {
    container.innerHTML = '<div class="content-title">Đang mở YouTube trên Brave Browser...</div>';
    await fetch(`/api/browser/youtube?token=${token}`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ query: '' })
    });
  } else if (appType === 'browser') {
    renderBrowserView(container);
  } else if (appType === 'iptv') {
    renderIPTVView(container);
  } else if (appType === 'movies') {
    renderMoviesView(container);
  } else if (appType === 'settings') {
    renderSettingsView(container);
  }
}

// Movies View
async function renderMoviesView(container) {
  container.innerHTML = '<div class="content-title">Đang quét danh sách phim offline...</div>';
  try {
    const res = await fetch(`/api/media/movies?token=${token}`, { headers: getHeaders() });
    const movies = await res.json();
    if (!movies.length) {
      container.innerHTML = `
        <div class="content-title">Phim của tôi</div>
        <p style="color:#94a3b8;">Không tìm thấy video nào trong thư mục media. Thêm tệp video (.mp4, .mkv) vào thư mục media để thưởng thức.</p>
      `;
      return;
    }
    let html = `<div class="content-title">Phim của tôi (${movies.length} tệp)</div><div class="list-scroll-grid">`;
    movies.forEach(m => {
      html += `
        <div class="media-item focusable" tabindex="0" data-path="${encodeURIComponent(m.path)}" data-title="${encodeURIComponent(m.title)}">
          <div class="m-title">▶ ${m.title}</div>
          <div class="m-meta">${m.size_mb} MB &bull; ${m.filename}</div>
        </div>
      `;
    });
    html += '</div>';
    container.innerHTML = html;

    container.querySelectorAll('.media-item').forEach(item => {
      item.addEventListener('click', async () => {
        const path = decodeURIComponent(item.dataset.path);
        const title = decodeURIComponent(item.dataset.title);
        await fetch(`/api/media/play?token=${token}`, {
          method: 'POST',
          headers: getHeaders(),
          body: JSON.stringify({ path, title })
        });
      });
    });
  } catch (err) {
    container.innerHTML = '<div class="content-title">Lỗi tải danh sách phim.</div>';
  }
}

// IPTV View
async function renderIPTVView(container) {
  container.innerHTML = '<div class="content-title">Đang tải danh sách kênh IPTV...</div>';
  try {
    const res = await fetch(`/api/iptv/channels?token=${token}`, { headers: getHeaders() });
    const channels = await res.json();
    if (!channels.length) {
      container.innerHTML = `
        <div class="content-title">Truyền hình IPTV</div>
        <p style="color:#94a3b8;">Chưa có kênh khả dụng. Dùng Q Remote để thêm liên kết M3U/M3U8 hợp lệ.</p>
      `;
      return;
    }
    let html = `<div class="content-title">Truyền hình IPTV (${channels.length} kênh)</div><div class="list-scroll-grid">`;
    channels.forEach(ch => {
      html += `
        <div class="media-item focusable" tabindex="0" data-url="${encodeURIComponent(ch.url)}" data-title="${encodeURIComponent(ch.title)}">
          <div class="m-title">📺 ${ch.title}</div>
          <div class="m-meta">${ch.group || 'IPTV Stream'}</div>
        </div>
      `;
    });
    html += '</div>';
    container.innerHTML = html;

    container.querySelectorAll('.media-item').forEach(item => {
      item.addEventListener('click', async () => {
        const url = decodeURIComponent(item.dataset.url);
        const title = decodeURIComponent(item.dataset.title);
        await fetch(`/api/iptv/play?token=${token}`, {
          method: 'POST',
          headers: getHeaders(),
          body: JSON.stringify({ url, title })
        });
      });
    });
  } catch (err) {
    container.innerHTML = '<div class="content-title">Lỗi kết nối IPTV.</div>';
  }
}

// Browser View
function renderBrowserView(container) {
  const sites = [
    { name: 'Google', url: 'https://www.google.com' },
    { name: 'VnExpress', url: 'https://vnexpress.net' },
    { name: 'Dân Trí', url: 'https://dantri.com.vn' },
    { name: 'Tuổi Trẻ Online', url: 'https://tuoitre.vn' }
  ];
  let html = '<div class="content-title">Trang web yêu thích (Mở bằng Brave)</div><div class="list-scroll-grid">';
  sites.forEach(s => {
    html += `
      <div class="media-item focusable" tabindex="0" data-url="${s.url}">
        <div class="m-title">🌐 ${s.name}</div>
        <div class="m-meta">${s.url}</div>
      </div>
    `;
  });
  html += '</div>';
  container.innerHTML = html;

  container.querySelectorAll('.media-item').forEach(item => {
    item.addEventListener('click', async () => {
      const url = item.dataset.url;
      await fetch(`/api/browser/open?token=${token}`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({ url })
      });
    });
  });
}

// Settings View
function renderSettingsView(container) {
  container.innerHTML = `
    <div class="content-title">Cài đặt & Hướng dẫn kết nối HDMI / Âm thanh</div>
    <div style="font-size:1.1rem; line-height:1.8; color:#cbd5e1;">
      <p>• <strong>Màn hình:</strong> Nhấn tổ hợp phím <code>Windows + P</code> trên máy tính, chọn <em>Duplicate</em> hoặc <em>Extend</em> để xuất hình ảnh sang TV.</p>
      <p>• <strong>Âm thanh:</strong> Nhấp vào biểu tượng Loa góc phải Taskbar Windows, chọn đầu ra là cổng <em>HDMI / TV Audio</em>.</p>
      <p>• <strong>Q Remote:</strong> Nhấn nút "📱 Kết nối Remote" phía trên góc phải để quét mã QR bằng camera điện thoại.</p>
    </div>
  `;
}

// Initial focus
window.addEventListener('DOMContentLoaded', () => {
  const firstCard = document.querySelector('.app-card');
  if (firstCard) firstCard.focus();
  renderMoviesView(document.getElementById('content-view'));
});
