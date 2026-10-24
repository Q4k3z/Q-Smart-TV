(() => {
  if (window !== top || document.getElementById('qsmart-web-controls')) return;
  const mount = () => {
    if (!document.documentElement || document.getElementById('qsmart-web-controls')) return;
    const host = document.createElement('div');
    host.id = 'qsmart-web-controls';
    host.style.cssText = 'position:fixed!important;top:8px!important;right:12px!important;z-index:2147483647!important;';
    const root = host.attachShadow({mode:'closed'});
    // DOM construction also works on sites enforcing Trusted Types (YouTube).
    const style = document.createElement('style');
    style.textContent = 'nav{display:flex;gap:6px;padding:6px;background:#151021ee;border:1px solid #9b7bd6;border-radius:12px;box-shadow:0 3px 16px #0008}button{font:600 16px system-ui;color:white;background:#352455;border:0;border-radius:8px;padding:10px 16px;cursor:pointer}button:hover{background:#7045a8}';
    const nav = document.createElement('nav');
    nav.setAttribute('aria-label', 'Q Smart TV');
    for (const [action, label] of [['back', '← Back'], ['home', '⌂ Về TV']]) {
      const button = document.createElement('button');
      button.type = 'button'; button.dataset.action = action; button.textContent = label;
      nav.appendChild(button);
    }
    root.append(style, nav);
    root.addEventListener('mousedown', e => e.preventDefault());
    root.addEventListener('click', e => {
      if (!e.isTrusted) return;
      const action = e.target.dataset.action;
      if (['back','home'].includes(action)) globalThis.qsmartNavigation(action);
    });
    (document.fullscreenElement || document.documentElement).appendChild(host);
    document.addEventListener('fullscreenchange', () => (document.fullscreenElement || document.documentElement).appendChild(host));
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount, {once:true});
  else mount();
})();
