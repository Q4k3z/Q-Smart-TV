// Loaded in the TV page, or in a private isolated world in our Brave tab.
(() => {
  if (globalThis.QSmartInput) return;
  let session = null;
  const active = () => {
    let el = document.activeElement;
    while (el?.shadowRoot?.activeElement) el = el.shadowRoot.activeElement;
    return el;
  };
  const check = id => {
    if (!session || session.id !== id || !session.el.isConnected || active() !== session.el || session.el.value !== session.expected)
      throw new Error('Ô nhập đã thay đổi. Chọn lại ô và bấm Bắt đầu nhập.');
    return session;
  };
  globalThis.QSmartInput = {
    start(id) {
      const el = active();
      if (!el?.matches('input,textarea') || el.disabled || el.readOnly || typeof el.selectionStart !== 'number')
        throw new Error('Hãy dùng chuột chọn ô nhập văn bản trên TV trước. Ô này cần hỗ trợ chọn văn bản.');
      session = {id, el, anchor:el.selectionStart, length:el.selectionEnd-el.selectionStart, expected:el.value, revision:0};
      return {ok:true};
    },
    prepare(id, revision) {
      const s = check(id);
      if (revision !== s.revision + 1) throw new Error('Phiên nhập không đồng bộ. Bấm Bắt đầu nhập lại.');
      s.el.setSelectionRange(s.anchor, s.anchor + s.length);
      s.applying = true;
      return {remove:s.length > 0};
    },
    commit(id, revision, text, start, end) {
      if (!session || session.id !== id) throw new Error('Phiên nhập đã kết thúc.');
      const s = session;
      const expected = s.expected.slice(0,s.anchor) + text + s.expected.slice(s.anchor+s.length);
      if (active() !== s.el) { session = null; throw new Error('Ô nhập đã mất focus. Chọn lại ô rồi bắt đầu lại.'); }
      if (s.el.value !== expected) return {pending:true};
      s.expected = expected; s.length = text.length; s.revision = revision; s.applying = false;
      s.el.setSelectionRange(s.anchor+start, s.anchor+end);
      return {ok:true};
    },
    apply(id, revision, text, start, end) {
      const {remove} = this.prepare(id, revision);
      const el = session.el;
      el.setRangeText(text, el.selectionStart, el.selectionEnd, 'end');
      el.dispatchEvent(new InputEvent('input', {bubbles:true, inputType:remove?'insertReplacementText':'insertText', data:text}));
      const result = this.commit(id, revision, text, start, end);
      if (result.pending) throw new Error('Ô nhập không nhận đúng nội dung. Chọn lại ô rồi bắt đầu lại.');
      return result;
    },
    end() { session = null; return {ok:true}; }
  };
  document.addEventListener('focusin', e => { if (session && e.target !== session.el) session = null; }, true);
  document.addEventListener('pointerdown', () => { session = null; }, true);
  document.addEventListener('keydown', e => { if (e.isTrusted && !session?.applying) session = null; }, true);
})();
