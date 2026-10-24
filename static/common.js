// Shared authenticated requests for both the TV and the phone.
window.QSmart = (() => {
  const url = new URL(location.href);
  const token = url.searchParams.get('token') || localStorage.getItem('qsmart_token') || '';
  if (token) localStorage.setItem('qsmart_token', token);
  if (url.searchParams.has('token')) {
    url.searchParams.delete('token');
    history.replaceState(null, '', url.pathname + url.search + url.hash);
  }
  const headers = () => ({ 'Content-Type': 'application/json', Authorization: `Bearer ${token}` });
  const pending = new Map();
  async function request(url, body = null, method = 'POST') {
    const key = JSON.stringify([url, body, method]);
    if (pending.has(key)) return pending.get(key);
    const button = document.activeElement?.closest('button');
    const task = (async () => {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 20000);
      if (button) { button.disabled = true; button.setAttribute('aria-busy', 'true'); }
      try {
        const res = await fetch(url, { method, headers: headers(), signal: controller.signal,
          ...(body === null ? {} : { body: JSON.stringify(body) }) });
        const data = await res.json();
        if (!res.ok || ['error', 'failed'].includes(data.status)) {
          const detail = res.status === 401 ? 'Chưa ghép nối. Quét mã QR mới trên TV để kết nối.' : (data.detail || data.message || 'Yêu cầu thất bại.');
          throw new Error(typeof detail === 'string' ? detail : 'Dữ liệu nhập chưa hợp lệ.');
        }
        return data;
      } catch (err) {
        if (err.name === 'AbortError') throw new Error('Máy chủ phản hồi quá chậm. Kiểm tra kết nối rồi thử lại.');
        if (err instanceof TypeError) throw new Error('Không thể kết nối máy chủ Q Smart TV.');
        throw err;
      } finally {
        clearTimeout(timer);
        if (button) { button.disabled = false; button.removeAttribute('aria-busy'); }
      }
    })();
    pending.set(key, task);
    try { return await task; } finally { pending.delete(key); }
  }
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));
  return { token, headers, request, escape };
})();
