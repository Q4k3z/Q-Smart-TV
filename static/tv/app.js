const { token, request: api, escape: esc } = QSmart;
const content = document.getElementById('content-view');
let currentView = 'home';
let focusBeforeModal = null;
let pairingIP = null;
function showError(message) {
  const el = document.getElementById('tv-alert');
  el.textContent = message;
  el.hidden = false;
}
function homeView() {
  currentView = 'home';
  content.innerHTML = '<div class="content-title">Chào mừng đến Q Smart TV</div><p>Chọn ứng dụng để bắt đầu. Bấm “Kết nối Remote” để ghép nối điện thoại cùng Wi-Fi.</p>';
  document.querySelector('.app-card').focus();
}
function updateClock() {
  const now = new Date();
  document.getElementById('time-display').textContent = now.toLocaleTimeString('vi-VN', {hour:'2-digit', minute:'2-digit'});
  document.getElementById('date-display').textContent = now.toLocaleDateString('vi-VN', {weekday:'long', day:'2-digit', month:'2-digit'});
}
updateClock();
setInterval(updateClock, 1000);
async function fetchSystemInfo() {
  try {
    const data = await api('/api/info', null, 'GET');
    document.getElementById('remote-ip-info').textContent = `IP: ${data.lan_ip} | Server online`;
    if (pairingIP !== data.lan_ip) {
      document.getElementById('qr-image').src = `/api/qrcode?token=${encodeURIComponent(token)}&v=${Date.now()}`;
      pairingIP = data.lan_ip;
    }
    document.getElementById('qr-url-display').textContent = data.remote_url;
    const select = document.getElementById('network-select');
    if (document.activeElement !== select) {
      select.replaceChildren(new Option('Tự chọn Ethernet / Wi-Fi', ''));
      data.network_interfaces.forEach(item => select.add(new Option(`${item.name}: ${item.ip}`, item.ip)));
      select.value = data.lan_ip;
    }
  } catch (err) { showError(err.message); }
}
function getFocusableElements() {
  const modal = document.querySelector('.modal-overlay.active');
  return Array.from((modal || document).querySelectorAll('.focusable')).filter(el => el.offsetParent !== null && !el.disabled);
}
function closeModal(id) {
  document.getElementById(id).classList.remove('active');
  (focusBeforeModal || document.querySelector('.app-card')).focus();
}
function openModal(id) {
  focusBeforeModal = document.activeElement;
  const modal = document.getElementById(id);
  modal.classList.add('active');
  modal.querySelector('.focusable').focus();
}
function handleKeyDown(e) {
  const current = document.activeElement;
  const editing = current?.matches('input,textarea,select');
  if (e.key === 'Home' && !editing) {
    e.preventDefault();
    document.querySelectorAll('.modal-overlay.active').forEach(el => el.classList.remove('active'));
    homeView();
    return;
  }
  if (e.key === 'Escape' || (e.key === 'Backspace' && !editing)) {
    e.preventDefault();
    const modal = document.querySelector('.modal-overlay.active');
    if (modal) closeModal(modal.id);
    else if (currentView !== 'home') homeView();
    return;
  }
  if (editing && !['ArrowUp','ArrowDown'].includes(e.key)) return;
  const elements = getFocusableElements();
  if (!elements.length) return;
  if (e.key === 'Enter') {
    e.preventDefault();
    (elements.includes(current) ? current : elements[0]).click();
    return;
  }
  if (!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key)) return;
  e.preventDefault();
  if (!elements.includes(current)) { elements[0].focus(); return; }
  const rect = current.getBoundingClientRect();
  const x = rect.left + rect.width / 2, y = rect.top + rect.height / 2;
  const horizontal = ['ArrowLeft','ArrowRight'].includes(e.key);
  const sign = ['ArrowRight','ArrowDown'].includes(e.key) ? 1 : -1;
  const candidates = elements.filter(el => el !== current).map(el => {
    const r = el.getBoundingClientRect();
    const dx = r.left + r.width / 2 - x, dy = r.top + r.height / 2 - y;
    return {el, forward: (horizontal ? dx : dy) * sign, cross: Math.abs(horizontal ? dy : dx)};
  }).filter(c => c.forward > 5).sort((a,b) => (a.forward + a.cross * 3) - (b.forward + b.cross * 3));
  if (candidates.length) {
    candidates[0].el.focus();
    candidates[0].el.scrollIntoView({block:'nearest'});
  }
}
document.addEventListener('keydown', handleKeyDown);
document.getElementById('tv-back-btn').onclick = () => handleKeyDown(new KeyboardEvent('keydown', {key:'Escape'}));
document.getElementById('tv-home-btn').onclick = homeView;
document.getElementById('network-select').onchange = async e => {
  try { await api('/api/network', {ip:e.target.value || null}); pairingIP = null; await fetchSystemInfo(); }
  catch (err) { showError(err.message); }
};
document.getElementById('exit-btn').onclick = () => openModal('exit-modal');
document.getElementById('qr-pairing-btn').onclick = () => openModal('qr-modal');
document.getElementById('btn-close-qr').onclick = () => closeModal('qr-modal');
document.getElementById('btn-cancel-exit').onclick = () => closeModal('exit-modal');
document.getElementById('btn-confirm-exit').onclick = async () => {
  try { await api('/api/launcher/exit'); } catch (err) { showError(err.message); }
};
function renderBrowser(searchOnly = false) {
  content.innerHTML = `<div class="content-title">${searchOnly ? 'Tìm video YouTube' : 'Trình duyệt'}</div><form id="browser-form"><input class="focusable" id="browser-input" inputmode="${searchOnly ? 'search' : 'url'}" autocapitalize="none" spellcheck="false" aria-label="${searchOnly ? 'Từ khóa YouTube' : 'URL website'}" placeholder="${searchOnly ? 'Nhập từ khóa' : 'youtube.com hoặc 192.168.1.3:8765'}"><button class="btn focusable" type="submit">Mở</button></form>`;
  document.getElementById('browser-form').onsubmit = async e => {
    e.preventDefault();
    const value = document.getElementById('browser-input').value.trim();
    if (!value) return;
    try { await api(searchOnly ? '/api/browser/youtube' : '/api/browser/open', searchOnly ? {query:value} : {url:value}); }
    catch (err) { showError(err.message); }
  };
  document.getElementById('browser-input').focus();
}
async function renderLibrary(kind) {
  content.innerHTML = '<div class="content-title">Đang tải...</div>';
  const movies = kind === 'movies';
  const items = await api(movies ? '/api/media/movies' : '/api/iptv/channels', null, 'GET');
  content.innerHTML = `<div class="content-title">${movies ? 'Phim của tôi' : 'Truyền hình IPTV'} (${items.length})</div><input id="library-search" class="focusable" aria-label="Tìm kiếm" placeholder="Tìm kiếm..."><div class="list-scroll-grid" id="library-list"></div>`;
  const list = document.getElementById('library-list');
  function render(q = '') {
    list.innerHTML = '';
    items.filter(item => item.title.toLowerCase().includes(q)).forEach(item => {
      const button = document.createElement('button');
      button.className = 'media-item focusable';
      button.innerHTML = `<div class="m-title">${esc(item.title)}</div><div class="m-meta">${esc(movies ? item.filename : item.group)}</div>`;
      button.onclick = async () => {
        try { await api(movies ? '/api/media/play' : '/api/iptv/play', movies ? {path:item.path,title:item.title} : {url:item.url,title:item.title}); }
        catch (err) { showError(err.message); }
      };
      list.appendChild(button);
    });
    if (!list.children.length) list.textContent = items.length ? 'Không có kết quả phù hợp.' : (movies ? 'Thêm video vào data/media hoặc cấu hình QSMART_ALLOWED_MEDIA_DIRS trong .env.' : 'Chưa có kênh. Thêm playlist bạn có quyền sử dụng bằng Q Remote.');
  }
  document.getElementById('library-search').oninput = e => render(e.target.value.toLowerCase());
  render();
  document.getElementById('library-search').focus();
}
async function handleAppClick(appType) {
  currentView = appType;
  document.getElementById('tv-alert').hidden = true;
  try {
    if (appType === 'youtube') await api('/api/browser/youtube', {query:''});
    else if (appType === 'browser' || appType === 'search') renderBrowser(appType === 'search');
    else if (appType === 'movies' || appType === 'iptv') await renderLibrary(appType);
    else if (appType === 'settings') {
      const info = await api('/api/info', null, 'GET');
      content.innerHTML = `<div class="content-title">Cài đặt & hướng dẫn</div><p>Brave: ${info.brave_available ? 'Đã tìm thấy' : 'Chưa tìm thấy — cài Brave hoặc đặt QSMART_BRAVE_PATH trong .env'}</p><p>mpv: ${info.mpv_available ? 'Đã tìm thấy' : 'Chưa tìm thấy — xem hướng dẫn cài mpv trong README'}</p><p>Windows + P: chọn Duplicate hoặc Extend. Chọn TV/HDMI trong đầu ra âm thanh Windows.</p><p>Đổi cổng, đường dẫn ứng dụng và thư mục phim qua .env (xem .env.example), sau đó khởi động lại server.</p>`;
    }
  } catch (err) { showError(err.message); }
}
document.querySelectorAll('.app-card').forEach(card => card.onclick = () => handleAppClick(card.dataset.app));
let socket, reconnectTimer, reconnectDelay = 1000;
function connectTV() {
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  socket = new WebSocket(`${protocol}//${location.host}/ws?role=tv&token=${encodeURIComponent(token)}`);
  socket.onopen = () => { reconnectDelay = 1000; fetchSystemInfo(); };
  socket.onmessage = event => {
    if (event.data === 'pong') return;
    const message = JSON.parse(event.data);
    if (message.event !== 'control') return;
    const data = message.data;
    if (data.action === 'input_call') {
      let result;
      try {
        if (!['start','apply','end'].includes(data.method)) throw new Error('Thao tác nhập không hợp lệ.');
        result = {ok:true, result:QSmartInput[data.method](...data.args)};
      } catch (err) { result = {ok:false, message:err.message}; }
      socket.send(JSON.stringify({event:'control_result',request_id:data.request_id,result}));
      return;
    }
    if (data.action === 'home') {
      document.querySelectorAll('.modal-overlay.active').forEach(el => el.classList.remove('active'));
      homeView();
    }
    if (data.action === 'back') handleKeyDown(new KeyboardEvent('keydown', {key:'Escape'}));
    if (data.action === 'key') {
      if (handleInputKey(data.key)) return;
      const keys = {UP:'ArrowUp',DOWN:'ArrowDown',LEFT:'ArrowLeft',RIGHT:'ArrowRight',ENTER:'Enter',TAB:'ArrowRight',SPACE:'Enter',ESCAPE:'Escape',HOME:'Home'};
      if (data.key === 'ENTER' && document.activeElement?.matches('input')) document.activeElement.form?.requestSubmit();
      else if (keys[data.key]) handleKeyDown(new KeyboardEvent('keydown', {key:keys[data.key]}));
    }
    if (data.action === 'text') {
      const input = document.activeElement;
      if (input?.matches('input,textarea')) { input.value += data.text; input.dispatchEvent(new Event('input', {bubbles:true})); }
      else showError('Hãy chọn ô nhập trước khi gửi văn bản từ remote.');
    }
  };
  socket.onclose = () => {
    document.getElementById('remote-ip-info').textContent = 'Mất kết nối máy chủ. Đang thử lại...';
    clearTimeout(reconnectTimer);
    reconnectTimer = setTimeout(connectTV, reconnectDelay);
    reconnectDelay = Math.min(reconnectDelay * 1.5, 10000);
  };
  socket.onerror = () => socket.close();
}
homeView();
if (token) { fetchSystemInfo(); connectTV(); }
else showError('Mở TV bằng start_smarttv.bat hoặc truy cập http://127.0.0.1:8765/ trên máy tính để ghép nối.');
setInterval(() => { if (token) fetchSystemInfo(); if (socket?.readyState === WebSocket.OPEN) socket.send('ping'); }, 15000);

function handleInputKey(key) {
  const el = document.activeElement;
  if (key === 'TAB' || key === 'SHIFT_TAB') {
    const list = getFocusableElements();
    const index = list.indexOf(el);
    list[index < 0 ? (key === 'TAB' ? 0 : list.length-1) : (index + (key === 'TAB' ? 1 : -1) + list.length) % list.length]?.focus();
    return true;
  }
  if (!el?.matches('input,textarea') || typeof el.selectionStart !== 'number') return false;
  let start = el.selectionStart, end = el.selectionEnd;
  const segments = Array.from(new Intl.Segmenter('vi', {granularity:'grapheme'}).segment(el.value));
  const before = segments.filter(s => s.index < start).at(-1)?.index ?? 0;
  const after = segments.find(s => s.index > end)?.index ?? el.value.length;
  if (key === 'BACKSPACE' || key === 'DELETE') {
    if (start === end) { if (key === 'BACKSPACE') start = before; else end = after; }
    el.setRangeText('',start,end,'end');
    el.dispatchEvent(new Event('input',{bubbles:true}));
  } else if (key === 'LEFT') el.setSelectionRange(start === end ? before : start, start === end ? before : start);
  else if (key === 'RIGHT') el.setSelectionRange(start === end ? after : end,start === end ? after : end);
  else if (key === 'HOME') el.setSelectionRange(0,0);
  else if (key === 'END') el.setSelectionRange(el.value.length,el.value.length);
  else if (key === 'UP' || key === 'DOWN') {
    const lines = el.value.split('\n');
    const lineIndex = el.value.slice(0,start).split('\n').length-1;
    const lineStart = lines.slice(0,lineIndex).reduce((sum,line) => sum+line.length+1,0);
    const nextIndex = Math.max(0,Math.min(lines.length-1,lineIndex+(key === 'UP' ? -1 : 1)));
    const nextStart = lines.slice(0,nextIndex).reduce((sum,line) => sum+line.length+1,0);
    const position = nextStart + Math.min(start-lineStart,lines[nextIndex].length);
    el.setSelectionRange(position,position);
  }
  else if (key === 'SELECT_ALL') el.select();
  else if (key === 'ENTER') el.form?.requestSubmit();
  else if (key === 'ESCAPE') el.blur();
  else return false;
  QSmartInput.end();
  return true;
}
