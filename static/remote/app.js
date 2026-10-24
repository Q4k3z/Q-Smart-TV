// Q Remote Client Logic
const { token, escape: esc } = QSmart;

const statusDot = document.getElementById('status-dot');
const statusText = document.getElementById('status-text');
const alertBanner = document.getElementById('alert-banner');
const reopenCard = document.getElementById('reopen-card');
const mediaPlayingBar = document.getElementById('media-playing-bar');
const mediaPlayingTitle = document.getElementById('media-playing-title');
const mediaBadge = document.getElementById('media-badge');

let alertTimer;
function showAlert(message, type = 'error', duration = 3000) {
  clearTimeout(alertTimer);
  alertBanner.textContent = message;
  alertBanner.className = `alert-banner ${type}`;
  if (duration > 0) {
    alertTimer = setTimeout(() => {
      alertBanner.className = 'alert-banner';
    }, duration);
  }
}

// API Call Wrapper
async function sendApi(url, body = null, method = 'POST') {
  try { return await QSmart.request(url, body, method); }
  catch (err) { showAlert(err.message, 'error', 8000); return null; }
}

// System State Application
function applyState(data) {
  if (!data) return;
  window.RemoteControls?.state(data);
  if (data.launcher === 'closed') {
    reopenCard.classList.add('visible');
  } else {
    reopenCard.classList.remove('visible');
  }
  statusDot.className = 'status-dot dot-online';
  const names = {launcher:'Trang chủ', youtube:'YouTube', browser:'Trình duyệt', movies:'Phim', iptv:'IPTV'};
  const appName = data.active_app ? ` | ${names[data.active_app] || data.active_app}` : '';
  statusText.textContent = `Server online | TV ${data.launcher === 'open' ? 'đang mở' : data.launcher === 'starting' ? 'đang mở...' : 'đã đóng'}${appName}`;

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
let reconnectTimer;
function connectWebSocket() {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${proto}//${window.location.host}/ws?token=${encodeURIComponent(token)}`;
  
  clearTimeout(reconnectTimer);
  if (ws && ws.readyState < 2) return;
  ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    window.RemoteControls?.connected(ws);
    reconnectDelay = 1000;
    statusDot.className = 'status-dot dot-online';
    statusText.textContent = 'Đã kết nối';
    fetchStatus();
  };

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      if (msg.event === 'input_result') { window.RemoteControls?.result(msg); return; }
      if (msg.event === 'state_changed' || msg.event === 'connected') {
        applyState(msg.data);
      }
    } catch (e) {}
  };

  ws.onclose = () => {
    window.RemoteControls?.disconnected();
    statusDot.className = 'status-dot dot-offline';
    statusText.textContent = 'Mất kết nối. Đang thử lại...';
    reconnectTimer = setTimeout(() => {
      reconnectDelay = Math.min(reconnectDelay * 1.5, 10000);
      connectWebSocket();
      fetchStatus();
    }, reconnectDelay);
  };

  ws.onerror = () => {
    ws.close();
  };
}

document.getElementById('btn-reconnect').onclick = () => { fetchStatus(); connectWebSocket(); };
if (token) { fetchStatus(); connectWebSocket(); }
else showAlert('Chưa ghép nối. Quét mã QR trên TV để kết nối.', 'error', 0);

// Navigation Controls
document.getElementById('btn-home').addEventListener('click', () => {
  window.RemoteControls?.end();
  sendApi('/api/control/home');
});

document.getElementById('btn-back').addEventListener('click', () => {
  window.RemoteControls?.end();
  sendApi('/api/control/back');
});

// Reopen TV
document.getElementById('btn-reopen-tv').addEventListener('click', async () => {
  const res = await sendApi('/api/launcher/open');
  if (res && ['success', 'already_running'].includes(res.status)) {
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
  window.RemoteControls?.end();
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

document.getElementById('form-url').addEventListener('submit', async (e) => {
  e.preventDefault();
  const input = document.getElementById('input-url');
  const url = input.value.trim();
  if (!url) return;
  const result = await sendApi('/api/browser/open', { url });
  if (result) {
    input.value = '';
    showAlert('Đã mở website.', 'success', 2000);
  }
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

// Main Section Tabs (Remote / Movies / IPTV)
const mainViews = {
  'tab-remote-view': 'view-remote',
  'tab-movies-view': 'view-movies',
  'tab-iptv-view': 'view-iptv'
};

let cachedMovies = [];
let cachedChannels = [];
let cachedFavorites = [];
let filterOnlyFavorites = false;

Object.entries(mainViews).forEach(([tabId, viewId]) => {
  document.getElementById(tabId).addEventListener('click', () => {
    document.querySelectorAll('.nav-tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-view').forEach(v => v.classList.remove('active'));
    document.getElementById(tabId).classList.add('active');
    document.getElementById(viewId).classList.add('active');

    if (viewId === 'view-movies' && !cachedMovies.length) {
      loadMoviesList();
    } else if (viewId === 'view-iptv') {
      loadPlaylistsDropdown();
      loadIPTVChannels();
    }
  });
});

// Movies List
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
        <div class="item-name">${esc(m.title)}</div>
        <div class="item-sub">${m.size_mb} MB &bull; ${esc(m.filename)}</div>
      </div>
      <div class="item-action-icon">▶</div>
    `;
    item.addEventListener('click', async () => {
      const result = await sendApi('/api/media/play', { path: m.path, title: m.title });
      if (result) showAlert(`Đang phát: ${m.title}`, 'info', 2000);
    });
    container.appendChild(item);
  });
}

document.getElementById('search-movies-input').addEventListener('input', (e) => {
  const q = e.target.value.toLowerCase().trim();
  const filtered = cachedMovies.filter(m => m.title.toLowerCase().includes(q) || m.filename.toLowerCase().includes(q));
  renderMovies(filtered);
});

// IPTV Playlists Dropdown
async function loadPlaylistsDropdown() {
  const select = document.getElementById('select-playlist');
  const playlists = await sendApi('/api/iptv/playlists', null, 'GET');
  if (playlists) {
    select.innerHTML = '<option value="">Tất cả kênh</option>';
    playlists.forEach(pl => {
      const opt = document.createElement('option');
      opt.value = pl.id;
      opt.textContent = pl.name;
      select.appendChild(opt);
    });
  }
}

document.getElementById('select-playlist').addEventListener('change', (e) => {
  const plId = e.target.value;
  loadIPTVChannels(plId);
});

// Load & Filter IPTV Channels
async function loadIPTVChannels(playlistId = '') {
  const container = document.getElementById('iptv-list-container');
  container.innerHTML = '<div class="loading-state">Đang tải danh sách kênh IPTV...</div>';
  
  const [channels, favorites] = await Promise.all([
    sendApi(playlistId ? `/api/iptv/channels?playlist_id=${encodeURIComponent(playlistId)}` : '/api/iptv/channels', null, 'GET'),
    sendApi('/api/iptv/favorites', null, 'GET')
  ]);

  if (channels) {
    cachedChannels = channels;
    cachedFavorites = favorites || [];
    filterAndRenderChannels();
  } else {
    container.innerHTML = '<div class="loading-state">Không thể tải danh sách kênh.</div>';
  }
}

function filterAndRenderChannels() {
  const q = document.getElementById('search-iptv-input').value.toLowerCase().trim();
  let list = cachedChannels;
  if (filterOnlyFavorites) {
    const favUrls = new Set(cachedFavorites.map(f => f.url));
    list = list.filter(ch => favUrls.has(ch.url));
  }
  if (q) {
    list = list.filter(ch => ch.title.toLowerCase().includes(q) || (ch.group && ch.group.toLowerCase().includes(q)));
  }
  renderChannels(list);
}

function renderChannels(channels) {
  const container = document.getElementById('iptv-list-container');
  if (!channels.length) {
    container.innerHTML = '<div class="loading-state">Không có kênh nào phù hợp.</div>';
    return;
  }
  container.innerHTML = '';
  const favUrls = new Set(cachedFavorites.map(f => f.url));

  channels.forEach(ch => {
    const isStarred = favUrls.has(ch.url);
    const item = document.createElement('div');
    item.className = 'list-item';
    item.innerHTML = `
      <div class="item-main">
        <div class="item-name">📺 ${esc(ch.title)}</div>
        <div class="item-sub">${esc(ch.group || 'IPTV Stream')}</div>
      </div>
      <div class="item-actions-group">
        <button class="star-btn ${isStarred ? 'starred' : ''}" title="Yêu thích">★</button>
        <div class="item-action-icon">▶</div>
      </div>
    `;

    // Click to Play
    item.querySelector('.item-main').addEventListener('click', async () => {
      const result = await sendApi('/api/iptv/play', { url: ch.url, title: ch.title });
      if (result) showAlert(`Đang phát: ${ch.title}`, 'info', 2000);
    });
    item.querySelector('.item-action-icon').addEventListener('click', async () => {
      const result = await sendApi('/api/iptv/play', { url: ch.url, title: ch.title });
      if (result) showAlert(`Đang phát: ${ch.title}`, 'info', 2000);
    });

    // Toggle Star
    const starBtn = item.querySelector('.star-btn');
    starBtn.addEventListener('click', async (e) => {
      e.stopPropagation();
      const res = await sendApi('/api/iptv/favorites', { channel: ch });
      if (res) {
        if (res.favorited) {
          cachedFavorites.push(ch);
          starBtn.classList.add('starred');
          showAlert(`Đã thêm ${ch.title} vào Yêu thích`, 'info', 1500);
        } else {
          cachedFavorites = cachedFavorites.filter(f => f.url !== ch.url);
          starBtn.classList.remove('starred');
          showAlert(`Đã bỏ ${ch.title} khỏi Yêu thích`, 'info', 1500);
        }
        if (filterOnlyFavorites) filterAndRenderChannels();
      }
    });

    container.appendChild(item);
  });
}

document.getElementById('search-iptv-input').addEventListener('input', filterAndRenderChannels);

// Favorites Filter Toggle
const btnFilterFav = document.getElementById('btn-filter-fav');
btnFilterFav.addEventListener('click', () => {
  filterOnlyFavorites = !filterOnlyFavorites;
  btnFilterFav.classList.toggle('active', filterOnlyFavorites);
  filterAndRenderChannels();
});

// Add Playlist Modal
const addPlaylistModal = document.getElementById('add-playlist-modal');
document.getElementById('btn-open-add-playlist').addEventListener('click', () => {
  addPlaylistModal.classList.add('active');
});

document.getElementById('btn-cancel-add-playlist').addEventListener('click', () => {
  addPlaylistModal.classList.remove('active');
});

document.getElementById('form-add-playlist').addEventListener('submit', async (e) => {
  e.preventDefault();
  const name = document.getElementById('playlist-name-input').value.trim();
  const url = document.getElementById('playlist-url-input').value.trim();
  if (name && url) {
    const res = await sendApi('/api/iptv/playlists', { name, url });
    if (res) {
      addPlaylistModal.classList.remove('active');
      showAlert(`Đã lưu playlist: ${name}`, 'info', 2000);
      document.getElementById('playlist-name-input').value = '';
      document.getElementById('playlist-url-input').value = '';
      await loadPlaylistsDropdown();
      loadIPTVChannels(res.id);
    }
  }
});
