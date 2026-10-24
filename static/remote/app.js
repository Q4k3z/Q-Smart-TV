// Q Remote Client Logic
const urlParams = new URLSearchParams(window.location.search);
let token = urlParams.get('token') || localStorage.getItem('qsmart_token') || '';
if (token) localStorage.setItem('qsmart_token', token);

const statusDot = document.getElementById('status-dot');
const statusText = document.getElementById('status-text');
const alertBanner = document.getElementById('alert-banner');
const reopenCard = document.getElementById('reopen-card');
const mediaPlayingBar = document.getElementById('media-playing-bar');
const mediaPlayingTitle = document.getElementById('media-playing-title');
const mediaBadge = document.getElementById('media-badge');

function getHeaders() {
  const h = { 'Content-Type': 'application/json' };
  if (token) h['Authorization'] = `Bearer ${token}`;
  return h;
}

function showAlert(message, type = 'error', duration = 3000) {
  alertBanner.textContent = message;
  alertBanner.className = `alert-banner ${type}`;
  if (duration > 0) {
    setTimeout(() => {
      alertBanner.className = 'alert-banner';
    }, duration);
  }
}

// API Call Wrapper
let isRequestPending = false;
async function sendApi(url, body = null, method = 'POST') {
  if (isRequestPending) return null;
  isRequestPending = true;

  try {
    const opts = { method, headers: getHeaders() };
    if (body) opts.body = JSON.stringify(body);
    const targetUrl = url.includes('?') ? `${url}&token=${token}` : `${url}?token=${token}`;

    const res = await fetch(targetUrl, opts);
    if (!res.ok) {
      let errDetail = 'Lỗi yêu cầu máy chủ.';
      try {
        const errJson = await res.json();
        if (errJson.detail) errDetail = errJson.detail;
      } catch (e) {}
      showAlert(errDetail, 'error');
      return null;
    }
    const data = await res.json();
    return data;
  } catch (err) {
    showAlert('Không thể kết nối đến máy chủ Q Smart TV.', 'error');
    return null;
  } finally {
    isRequestPending = false;
  }
}

// System State Application
function applyState(data) {
  if (!data) return;
  // Launcher visibility
  if (data.launcher === 'closed') {
    reopenCard.classList.add('visible');
  } else {
    reopenCard.classList.remove('visible');
  }
  // Online indicator
  statusDot.className = 'status-dot dot-online';
  const appName = data.active_app ? ` | ${data.active_app.toUpperCase()}` : '';
  statusText.textContent = `Online${appName}`;

  // Media playback feedback
  if (data.mpv && data.mpv !== 'stopped' && data.mpv !== 'error') {
    mediaPlayingBar.classList.add('active');
    mediaBadge.textContent = data.mpv === 'playing' ? 'Đang phát' : 'Tạm dừng';
    const title = (data.current_media && data.current_media.title) ? data.current_media.title : 'Media Player';
    mediaPlayingTitle.textContent = title;
  } else {
    mediaPlayingBar.classList.remove('active');
  }
}

async function fetchStatus() {
  const data = await sendApi('/api/status', null, 'GET');
  if (data) {
    applyState(data);
  } else {
    statusDot.className = 'status-dot dot-offline';
    statusText.textContent = 'Mất kết nối';
  }
}

// WebSocket Live Updates
let ws = null;
let reconnectDelay = 1000;
function connectWebSocket() {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${proto}//${window.location.host}/ws?token=${token}`;
  
  ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    reconnectDelay = 1000;
    statusDot.className = 'status-dot dot-online';
    statusText.textContent = 'Đã kết nối';
  };

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      if (msg.event === 'state_changed' || msg.event === 'connected') {
        applyState(msg.data);
      }
    } catch (e) {}
  };

  ws.onclose = () => {
    statusDot.className = 'status-dot dot-offline';
    statusText.textContent = 'Mất kết nối. Đang thử lại...';
    setTimeout(() => {
      reconnectDelay = Math.min(reconnectDelay * 1.5, 10000);
      connectWebSocket();
      fetchStatus();
    }, reconnectDelay);
  };

  ws.onerror = () => {
    ws.close();
  };
}

fetchStatus();
connectWebSocket();

// Navigation Controls
document.getElementById('btn-home').addEventListener('click', () => {
  sendApi('/api/control/home');
});

document.getElementById('btn-back').addEventListener('click', () => {
  sendApi('/api/control/back');
});

// Reopen TV
document.getElementById('btn-reopen-tv').addEventListener('click', async () => {
  const res = await sendApi('/api/launcher/open');
  if (res && res.status === 'success') {
    reopenCard.classList.remove('visible');
    showAlert('Đang mở màn hình TV...', 'info', 2000);
  }
});

// Exit TV Modal
const exitModal = document.getElementById('exit-modal');
document.getElementById('btn-exit-tv').addEventListener('click', () => {
  exitModal.classList.add('active');
});

document.getElementById('modal-btn-cancel').addEventListener('click', () => {
  exitModal.classList.remove('active');
});

document.getElementById('modal-btn-confirm').addEventListener('click', async () => {
  exitModal.classList.remove('active');
  const res = await sendApi('/api/launcher/exit');
  if (res) {
    reopenCard.classList.add('visible');
    showAlert('Đã đóng TV. Server vẫn chạy nền.', 'info', 3000);
  }
});

// D-Pad Controls
const keyMap = {
  'btn-up': 'UP',
  'btn-down': 'DOWN',
  'btn-left': 'LEFT',
  'btn-right': 'RIGHT',
  'btn-ok': 'ENTER'
};

Object.entries(keyMap).forEach(([btnId, key]) => {
  document.getElementById(btnId).addEventListener('click', () => {
    sendApi('/api/control/press', { key });
  });
});

// Media Controls
document.getElementById('btn-play-pause').addEventListener('click', () => {
  sendApi('/api/media/pause');
});

document.getElementById('btn-seek-back').addEventListener('click', () => {
  sendApi('/api/media/seek', { seconds: -10 });
});

document.getElementById('btn-seek-forward').addEventListener('click', () => {
  sendApi('/api/media/seek', { seconds: 10 });
});

document.getElementById('btn-vol-down').addEventListener('click', () => {
  sendApi('/api/media/volume', { delta: -5 });
});

document.getElementById('btn-vol-up').addEventListener('click', () => {
  sendApi('/api/media/volume', { delta: 5 });
});

document.getElementById('btn-vol-mute').addEventListener('click', () => {
  sendApi('/api/control/press', { key: 'MUTE' });
});

document.getElementById('btn-media-quick-stop').addEventListener('click', () => {
  sendApi('/api/media/stop');
});

// Input Tabs
const tabs = {
  'tab-yt': 'form-yt',
  'tab-url': 'form-url',
  'tab-text': 'form-text'
};

Object.entries(tabs).forEach(([tabId, formId]) => {
  document.getElementById(tabId).addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.action-form').forEach(f => f.classList.remove('active'));
    document.getElementById(tabId).classList.add('active');
    document.getElementById(formId).classList.add('active');
  });
});

document.getElementById('form-yt').addEventListener('submit', (e) => {
  e.preventDefault();
  const input = document.getElementById('input-yt');
  const query = input.value.trim();
  sendApi('/api/browser/youtube', { query });
  input.value = '';
  showAlert('Đang mở YouTube...', 'info', 2000);
});

document.getElementById('form-url').addEventListener('submit', (e) => {
  e.preventDefault();
  const input = document.getElementById('input-url');
  let url = input.value.trim();
  if (url && !url.startsWith('http://') && !url.startsWith('https://')) {
    url = 'https://' + url;
  }
  sendApi('/api/browser/open', { url });
  input.value = '';
  showAlert('Đang mở website...', 'info', 2000);
});

document.getElementById('form-text').addEventListener('submit', (e) => {
  e.preventDefault();
  const input = document.getElementById('input-text');
  const text = input.value;
  if (text) {
    sendApi('/api/control/text', { text });
    input.value = '';
  }
});

// Main Section Tabs Switching (Remote vs Movies vs IPTV)
const mainViews = {
  'tab-remote-view': 'view-remote',
  'tab-movies-view': 'view-movies',
  'tab-iptv-view': 'view-iptv'
};

let cachedMovies = [];
let cachedChannels = [];

Object.entries(mainViews).forEach(([tabId, viewId]) => {
  document.getElementById(tabId).addEventListener('click', () => {
    document.querySelectorAll('.nav-tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-view').forEach(v => v.classList.remove('active'));
    document.getElementById(tabId).classList.add('active');
    document.getElementById(viewId).classList.add('active');

    if (viewId === 'view-movies' && !cachedMovies.length) {
      loadMoviesList();
    } else if (viewId === 'view-iptv' && !cachedChannels.length) {
      loadIPTVChannels();
    }
  });
});

// Load & Filter Movies
async function loadMoviesList() {
  const container = document.getElementById('movies-list-container');
  container.innerHTML = '<div class="loading-state">Đang quét danh sách phim...</div>';
  const movies = await sendApi('/api/media/movies', null, 'GET');
  if (movies) {
    cachedMovies = movies;
    renderMovies(movies);
  } else {
    container.innerHTML = '<div class="loading-state">Không thể tải danh sách phim.</div>';
  }
}

function renderMovies(movies) {
  const container = document.getElementById('movies-list-container');
  if (!movies.length) {
    container.innerHTML = '<div class="loading-state">Không có tệp phim nào phù hợp.</div>';
    return;
  }
  container.innerHTML = '';
  movies.forEach(m => {
    const item = document.createElement('div');
    item.className = 'list-item';
    item.innerHTML = `
      <div class="item-main">
        <div class="item-name">${m.title}</div>
        <div class="item-sub">${m.size_mb} MB &bull; ${m.filename}</div>
      </div>
      <div class="item-action-icon">▶</div>
    `;
    item.addEventListener('click', async () => {
      showAlert(`Đang phát: ${m.title}`, 'info', 2000);
      await sendApi('/api/media/play', { path: m.path, title: m.title });
    });
    container.appendChild(item);
  });
}

document.getElementById('search-movies-input').addEventListener('input', (e) => {
  const q = e.target.value.toLowerCase().trim();
  const filtered = cachedMovies.filter(m => m.title.toLowerCase().includes(q) || m.filename.toLowerCase().includes(q));
  renderMovies(filtered);
});

// Load & Filter IPTV Channels
async function loadIPTVChannels() {
  const container = document.getElementById('iptv-list-container');
  container.innerHTML = '<div class="loading-state">Đang tải danh sách kênh IPTV...</div>';
  const channels = await sendApi('/api/iptv/channels', null, 'GET');
  if (channels) {
    cachedChannels = channels;
    renderChannels(channels);
  } else {
    container.innerHTML = '<div class="loading-state">Không thể tải danh sách kênh.</div>';
  }
}

function renderChannels(channels) {
  const container = document.getElementById('iptv-list-container');
  if (!channels.length) {
    container.innerHTML = '<div class="loading-state">Không có kênh nào khả dụng.</div>';
    return;
  }
  container.innerHTML = '';
  channels.forEach(ch => {
    const item = document.createElement('div');
    item.className = 'list-item';
    item.innerHTML = `
      <div class="item-main">
        <div class="item-name">📺 ${ch.title}</div>
        <div class="item-sub">${ch.group || 'IPTV Stream'}</div>
      </div>
      <div class="item-action-icon">▶</div>
    `;
    item.addEventListener('click', async () => {
      showAlert(`Đang phát: ${ch.title}`, 'info', 2000);
      await sendApi('/api/iptv/play', { url: ch.url, title: ch.title });
    });
    container.appendChild(item);
  });
}

document.getElementById('search-iptv-input').addEventListener('input', (e) => {
  const q = e.target.value.toLowerCase().trim();
  const filtered = cachedChannels.filter(ch => ch.title.toLowerCase().includes(q) || (ch.group && ch.group.toLowerCase().includes(q)));
  renderChannels(filtered);
});
