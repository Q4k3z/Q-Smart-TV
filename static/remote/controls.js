(() => {
  let socket, serial = 0, mode = 'tv', app = null, live = false, composing = false;
  let epoch = 0, revision = 0, dirty = false, flushing = false;
  let hasTyped = false;
  const pending = new Map();
  const area = document.getElementById('live-text');
  const status = document.getElementById('typing-status');
  const pad = document.getElementById('touchpad');
  const sensitivity = document.getElementById('mouse-sensitivity');
  sensitivity.value = localStorage.getItem('qsmart_mouse_sensitivity') || '1.4';
  sensitivity.oninput = () => localStorage.setItem('qsmart_mouse_sensitivity', sensitivity.value);
  function request(action, data = {}) {
    if (socket?.readyState !== WebSocket.OPEN) return Promise.reject(new Error('Q Remote chưa kết nối. Hãy kết nối lại trước.'));
    const id = serial = (serial + 1) % 2147483647;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => { pending.delete(id); reject(new Error('Thao tác hết thời gian chờ. Không tự gửi lại để tránh gõ trùng.')); }, 8000);
      pending.set(id, {resolve,reject,timer});
      socket.send(JSON.stringify({id,action,...data}));
    });
  }
  function finish(message = 'Phiên nhập đã kết thúc. Chọn ô rồi bấm Bắt đầu nhập.') {
    epoch++; live = false; dirty = false; composing = false; area.disabled = true;
    status.textContent = message;
    document.getElementById('input-start').disabled = socket?.readyState !== WebSocket.OPEN;
  }
  function end() {
    finish();
    pointers.clear(); dx = dy = wheel = 0; dragging = false;
    document.getElementById('mouse-drag').classList.remove('active');
    if (socket?.readyState === WebSocket.OPEN) request('input_end').catch(() => {});
  }
  function setMode(value, notify = true) {
    if (value !== mode && notify) end();
    mode = value;
    for (const name of ['tv','mouse','keyboard']) {
      const button = document.getElementById(`mode-${name}`);
      button.classList.toggle('active', name === value);
      button.setAttribute('aria-pressed', String(name === value));
    }
    document.querySelector('.dpad-section').hidden = value !== 'tv';
    document.getElementById('mouse-panel').hidden = value !== 'mouse';
    document.getElementById('keyboard-panel').hidden = value !== 'keyboard';
  }
  for (const name of ['tv','mouse','keyboard']) document.getElementById(`mode-${name}`).onclick = () => setMode(name);
  document.getElementById('input-start').onclick = async () => {
    finish('Đang chọn ô nhập…');
    const current = epoch;
    document.getElementById('input-start').disabled = true;
    try {
      await request('input_start');
      if (current !== epoch) return;
      live = true; revision = 0; hasTyped = false; area.value = ''; area.disabled = false; area.focus();
      status.textContent = 'Đang nhập trực tiếp · Chỉ sửa đoạn bạn gõ từ điện thoại';
    } catch (err) { if (current === epoch) { finish(err.message); showAlert(err.message); } }
    finally { document.getElementById('input-start').disabled = socket?.readyState !== WebSocket.OPEN; }
  };
  document.getElementById('input-end').onclick = end;
  async function flush() {
    if (flushing || !live || composing) return;
    flushing = true;
    const current = epoch;
    try {
      while (dirty && live && !composing && current === epoch) {
        dirty = false;
        const snapshot = {text:area.value,start:area.selectionStart,end:area.selectionEnd,revision:++revision};
        await request('input_update',snapshot);
        if (current === epoch) status.textContent = 'Đã cập nhật trên TV/laptop';
      }
    } catch (err) { if (current === epoch) { finish(err.message); showAlert(err.message,'error',8000); } }
    finally { flushing = false; if (dirty && live && !composing) queueMicrotask(flush); }
  }
  function changed() { if (live) { dirty = true; flush(); } }
  area.addEventListener('compositionstart', () => { composing = true; });
  area.addEventListener('compositionend', () => { composing = false; hasTyped = true; changed(); });
  area.addEventListener('input', e => { hasTyped = true; if (!e.isComposing) changed(); });
  area.addEventListener('select', () => { if (hasTyped) changed(); });
  document.addEventListener('selectionchange', () => { if (hasTyped && document.activeElement === area) changed(); });
  document.querySelectorAll('[data-input-key]').forEach(button => {
    button.onclick = async () => {
      end();
      try { await request('key',{key:button.dataset.inputKey}); }
      catch (err) { showAlert(err.message); }
    };
  });
  const pointers = new Map();
  let multi = false, dx = 0, dy = 0, wheel = 0, moving = false, dragging = false;
  async function motion() {
    if (moving || socket?.readyState !== WebSocket.OPEN || socket.bufferedAmount > 16000) return;
    if (!dx && !dy && !wheel) return;
    moving = true;
    const x = Math.max(-500,Math.min(500,Math.round(dx)));
    const y = Math.max(-500,Math.min(500,Math.round(dy)));
    const w = Math.max(-1200,Math.min(1200,Math.round(wheel)));
    dx = dy = wheel = 0;
    try { await request('mouse',{mouse:w?'wheel':'move',dx:x,dy:y,wheel:w}); }
    catch (err) { dx = dy = wheel = 0; showAlert(err.message); }
    finally { moving = false; }
  }
  async function mouse(action, button='left') {
    try { await motion(); await request('mouse',{mouse:action,button}); }
    catch (err) { showAlert(err.message); }
  }
  pad.addEventListener('pointerdown', e => {
    e.preventDefault(); pad.setPointerCapture(e.pointerId);
    pointers.set(e.pointerId,{x:e.clientX,y:e.clientY,startX:e.clientX,startY:e.clientY,time:performance.now(),moved:false});
    if (pointers.size > 1) multi = true;
    pad.classList.add('touching');
  });
  pad.addEventListener('pointermove', e => {
    const point = pointers.get(e.pointerId);
    if (!point) return;
    const x = e.clientX - point.x, y = e.clientY - point.y;
    if (Math.hypot(e.clientX-point.startX,e.clientY-point.startY) > 6) point.moved = true;
    point.x = e.clientX; point.y = e.clientY;
    if (pointers.size >= 2) wheel -= y * 2;
    else if (!multi) { dx += x * Number(sensitivity.value); dy += y * Number(sensitivity.value); }
  });
  function pointerEnd(e) {
    const point = pointers.get(e.pointerId);
    if (!point) return;
    pointers.delete(e.pointerId);
    if (e.type === 'pointerup' && !multi && !dragging && !point.moved && performance.now()-point.time < 500) mouse('click');
    if (!pointers.size) { multi = false; pad.classList.remove('touching'); }
    if (e.type === 'pointercancel') { dx = dy = wheel = 0; request('release').catch(() => {}); }
  }
  pad.addEventListener('pointerup',pointerEnd);
  pad.addEventListener('pointercancel',pointerEnd);
  document.getElementById('mouse-left').onclick = () => mouse('click');
  document.getElementById('mouse-right').onclick = () => mouse('click','right');
  const drag = document.getElementById('mouse-drag');
  drag.addEventListener('pointerdown',e => { e.preventDefault(); drag.setPointerCapture(e.pointerId); dragging = true; mouse('down'); drag.classList.add('active'); });
  const stopDrag = () => { if (dragging) { dragging = false; mouse('up'); drag.classList.remove('active'); } };
  drag.addEventListener('pointerup',stopDrag);
  drag.addEventListener('pointercancel',stopDrag);
  setInterval(() => { if (mode === 'mouse') motion(); }, 33);
  setInterval(() => { if (socket?.readyState === WebSocket.OPEN) socket.send('ping'); }, 5000);
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) { end(); stopDrag(); request('release').catch(() => {}); }
  });
  window.RemoteControls = {
    connected(ws) { socket = ws; finish('Chọn ô trên TV rồi bấm Bắt đầu nhập.'); },
    disconnected() {
      socket = null; finish('Mất kết nối. Bắt đầu phiên mới sau khi kết nối lại.');
      pointers.clear(); dx = dy = wheel = 0; dragging = false; drag.classList.remove('active');
      for (const p of pending.values()) { clearTimeout(p.timer); p.reject(new Error('Kết nối đã ngắt.')); }
      pending.clear();
    },
    result(message) {
      const item = pending.get(message.id);
      if (!item) return;
      clearTimeout(item.timer); pending.delete(message.id);
      if (message.data.status === 'error' || message.data.status === 'failed') item.reject(new Error(message.data.message || 'Không thực hiện được thao tác.'));
      else item.resolve(message.data);
    },
    state(data) {
      const names = {launcher:'Q Smart TV',youtube:'YouTube trên Brave TV',browser:'Brave TV',movies:'Phim',iptv:'IPTV'};
      document.getElementById('control-target').textContent = `Đang điều khiển: ${names[data.active_app] || 'Chưa chọn ứng dụng'}`;
      if (app !== data.active_app) {
        if (app !== null) end();
        app = data.active_app;
        setMode(['browser','youtube'].includes(app) ? 'mouse' : 'tv',false);
      }
    }, end, request
  };
  // The socket may have connected before this script finished loading.
  if (typeof ws !== 'undefined' && ws?.readyState === WebSocket.OPEN) RemoteControls.connected(ws);
  if (typeof fetchStatus === 'function') fetchStatus();
})();
