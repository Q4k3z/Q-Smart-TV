"""Real Brave + phone-sized browser check for the approved remote features.

Run start_smarttv.bat first. Only Q Smart TV's private profiles are used.
"""
import sys
import json
import time
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
if hasattr(sys.stdout,'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr,'reconfigure'): sys.stderr.reconfigure(encoding='utf-8')
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from playwright.sync_api import sync_playwright, expect
from config import settings
from core.window_manager import find_visible_window_for_pids, get_process_family_pids, user32
import ctypes
from ctypes import wintypes
import psutil

BASE = f'http://127.0.0.1:{settings.PORT}'
HEADERS = {'Authorization':f'Bearer {settings.AUTH_TOKEN}','Content-Type':'application/json'}

def api(path,body=None):
    req = urllib.request.Request(BASE+path,headers=HEADERS,data=json.dumps(body).encode() if body is not None else None)
    with urllib.request.urlopen(req,timeout=25) as response: return json.load(response)

class Sample(BaseHTTPRequestHandler):
    def do_GET(self):
        body = f'''<!doctype html><meta charset="utf-8"><title>Sample {self.path}</title><style>body{{font:24px system-ui;background:#eef;color:#111;margin:60px}}input{{font:24px system-ui;width:80%;padding:12px}}#click{{position:fixed;left:50%;top:50%;transform:translate(-50%,-50%);width:600px;height:180px;font:30px system-ui}}</style><h1>Sample {self.path}</h1><input id="typing" value="Giữ: "><p><a id="popup" target="_blank" href="/three">Open third page</a></p><button id="click" onclick="this.dataset.count=Number(this.dataset.count||0)+1">Native mouse click</button><div style="height:2000px"></div>'''.encode()
        self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Security-Policy', "require-trusted-types-for 'script'");self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    def log_message(self,*args): pass


def run():
    server = ThreadingHTTPServer(('127.0.0.1',0),Sample)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    sample = f'http://127.0.0.1:{server.server_port}'
    errors=[]
    try:
        info = api('/api/info')
        assert any(item['ip'] == info['lan_ip'] for item in info['network_interfaces']), 'Select an active physical LAN interface.'
        assert api('/api/control/home',{})['status'] == 'success'
        opened = api('/api/browser/open',{'url':sample.removeprefix('http://')+'/one'})
        assert opened['status'] == 'success', opened
        port = int((settings.DATA_DIR/'brave-external-profile'/'DevToolsActivePort').read_text().splitlines()[0])
        with sync_playwright() as p:
            managed = p.chromium.connect_over_cdp(f'http://127.0.0.1:{port}')
            context = managed.contexts[0]
            web = context.pages[0]
            expect(web).to_have_url(sample+'/one')
            expect(web.locator('#qsmart-web-controls')).to_be_attached()
            phone_browser = p.chromium.launch(executable_path=settings.BRAVE_PATH,headless=True)
            phone = phone_browser.new_page(viewport={'width':390,'height':844},has_touch=True,is_mobile=True)
            phone.on('pageerror',lambda error:errors.append(str(error)))
            phone.goto(BASE+'/remote?token='+settings.AUTH_TOKEN)
            expect(phone.locator('#control-target')).to_contain_text('Brave')
            expect(phone.locator('#mouse-panel')).to_be_visible()
            phone.screenshot(path=str(settings.DATA_DIR/'logs'/'remote-mouse-verified.png'),full_page=True)
            web.evaluate("const d=document.createElement('dialog');d.id='test-modal';d.textContent='Test modal';document.body.append(d);d.showModal()")
            phone.locator('#btn-back').click()
            expect(web.locator('#test-modal')).not_to_be_visible()
            expect(web).to_have_url(sample+'/one')
            # Programmatic website opens must reuse the same target and preserve history.
            original_target = web.url
            for index, path in enumerate(('/two','/one','/two')):
                if index == 0:
                    phone.locator('#tab-url').click()
                    phone.locator('#input-url').fill('file:///C:/Windows')
                    phone.locator('#form-url button').click()
                    expect(phone.locator('#alert-banner')).to_contain_text('Địa chỉ website không hợp lệ')
                    expect(phone.locator('#input-url')).to_have_value('file:///C:/Windows')
                    phone.locator('#input-url').fill(sample.removeprefix('http://')+path)
                    phone.locator('#form-url button').click()
                    expect(phone.locator('#input-url')).to_have_value('')
                else:
                    assert api('/api/browser/open',{'url':sample+path})['status'] == 'success'
                expect(web).to_have_url(sample+path)
                assert len([page for page in context.pages if not page.is_closed()]) == 1
            phone.locator('#btn-back').click()
            expect(web).to_have_url(sample+'/one')
            # Links requesting a new tab also return into the main managed page.
            web.locator('#popup').click()
            expect(web).to_have_url(sample+'/three')
            web.wait_for_function('document.title.includes("/three")')
            for _ in range(30):
                if len([page for page in context.pages if not page.is_closed()]) == 1: break
                phone.wait_for_timeout(50)
            assert len([page for page in context.pages if not page.is_closed()]) == 1
            # Native mouse movement/click: position cursor at the owned window center.
            expected = f'--user-data-dir={settings.DATA_DIR / "brave-external-profile"}'.casefold()
            root = next(proc for proc in psutil.process_iter(['cmdline']) if expected in [a.casefold() for a in proc.info['cmdline'] or []] and not any(a.startswith('--type=') for a in proc.info['cmdline'] or []))
            hwnd = find_visible_window_for_pids(get_process_family_pids(root.pid))
            user32.SetThreadDpiAwarenessContext(ctypes.c_void_p(-4))
            rect = wintypes.RECT(); user32.GetWindowRect(hwnd,ctypes.byref(rect))
            user32.SetCursorPos((rect.left+rect.right)//2,(rect.top+rect.bottom)//2)
            phone.locator('#mouse-left').click()
            expect(web.locator('#click')).to_have_attribute('data-count','1')
            before=wintypes.POINT();user32.GetCursorPos(ctypes.byref(before))
            pad = phone.locator('#touchpad').bounding_box()
            phone.mouse.move(pad['x']+40,pad['y']+40)
            phone.mouse.down()
            phone.mouse.move(pad['x']+90,pad['y']+70,steps=5)
            phone.mouse.up()
            phone.wait_for_timeout(150)
            after=wintypes.POINT();user32.GetCursorPos(ctypes.byref(after))
            assert (after.x,after.y) != (before.x,before.y)
            # Hold/release and actual wheel events go through SendInput.
            phone.evaluate("RemoteControls.request('mouse',{mouse:'down'})")
            phone.evaluate("RemoteControls.request('mouse',{mouse:'up'})")
            phone.evaluate("RemoteControls.request('mouse',{mouse:'wheel',wheel:-360})")
            web.wait_for_function('window.scrollY > 0')
            scroll = web.evaluate('window.scrollY')
            touch = phone.context.new_cdp_session(phone)
            points = [{'id':1,'x':pad['x']+80,'y':pad['y']+80}, {'id':2,'x':pad['x']+140,'y':pad['y']+80}]
            touch.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':points})
            touch.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{**point,'y':point['y']+45} for point in points]})
            touch.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
            web.wait_for_function('(previous) => window.scrollY > previous',arg=scroll)
            # A disconnected phone cannot leave the Windows mouse button held.
            phone.evaluate("RemoteControls.request('mouse',{mouse:'down'})")
            assert user32.GetAsyncKeyState(1) & 0x8000
            phone.evaluate('ws.close()')
            for _ in range(30):
                if not (user32.GetAsyncKeyState(1) & 0x8000): break
                phone.wait_for_timeout(50)
            assert not (user32.GetAsyncKeyState(1) & 0x8000)
            phone.wait_for_function('ws?.readyState === WebSocket.OPEN')
            expect(phone.locator('#status-text')).to_contain_text('Server online',timeout=10000)
            web.evaluate('window.scrollTo(0,0)')
            # Live native Unicode input, replacement, deletion, emoji and IME composition.
            web.locator('#typing').click()
            web.locator('#typing').evaluate('el => el.setSelectionRange(el.value.length,el.value.length)')
            phone.locator('#mode-keyboard').click()
            phone.locator('#input-start').click()
            try:
                expect(phone.locator('#live-text')).to_be_enabled()
            except AssertionError as error:
                raise AssertionError(phone.locator('#typing-status').inner_text()) from error
            phone.locator('#live-text').fill('xin chào 📺')
            expect(web.locator('#typing')).to_have_value('Giữ: xin chào 📺')
            phone.locator('#live-text').fill('đã sửa tiếng Việt ✨')
            expect(web.locator('#typing')).to_have_value('Giữ: đã sửa tiếng Việt ✨')
            phone.locator('#live-text').evaluate("el => { el.setSelectionRange(3,6); el.setRangeText('chỉnh',3,6,'end'); el.dispatchEvent(new InputEvent('input',{bubbles:true,inputType:'insertReplacementText',data:'chỉnh'})); }")
            expect(web.locator('#typing')).to_have_value('Giữ: đã chỉnh tiếng Việt ✨')
            phone.locator('#live-text').fill('')
            expect(web.locator('#typing')).to_have_value('Giữ: ')
            phone.locator('#live-text').evaluate('''el => { el.dispatchEvent(new CompositionEvent('compositionstart',{bubbles:true})); el.value='Tiế';el.dispatchEvent(new InputEvent('input',{bubbles:true,isComposing:true})); }''')
            phone.wait_for_timeout(150)
            expect(web.locator('#typing')).to_have_value('Giữ: ')
            phone.locator('#live-text').evaluate('''el => { el.value='Tiếng Việt';el.setSelectionRange(10,10);el.dispatchEvent(new CompositionEvent('compositionend',{bubbles:true,data:'Tiếng Việt'}));el.dispatchEvent(new InputEvent('input',{bubbles:true})); }''')
            expect(web.locator('#typing')).to_have_value('Giữ: Tiếng Việt')
            expect(phone.locator('#alert-banner')).to_have_class('alert-banner',timeout=10000)
            phone.screenshot(path=str(settings.DATA_DIR/'logs'/'remote-keyboard-verified.png'),full_page=True)
            # Backspace edits the field, not browser history.
            phone.locator('[data-input-key=BACKSPACE]').click()
            expect(web.locator('#typing')).to_have_value('Giữ: Tiếng Việ')
            web.locator('#typing').click()
            phone.locator('#keyboard-panel [data-input-key=TAB]').click()
            expect(web.locator('#popup')).to_be_focused()
            phone.locator('#keyboard-panel [data-input-key=SHIFT_TAB]').click()
            expect(web.locator('#typing')).to_be_focused()
            phone.locator('[data-input-key=SELECT_ALL]').click()
            phone.locator('[data-input-key=DELETE]').click()
            expect(web.locator('#typing')).to_have_value('')
            expect(web).to_have_url(sample+'/three')
            # Changing the target ends live input without writing into the other field.
            phone.locator('#input-start').click()
            expect(phone.locator('#live-text')).to_be_enabled()
            web.locator('#click').click()
            phone.locator('#live-text').fill('must not be typed')
            expect(phone.locator('#live-text')).to_be_disabled()
            expect(web.locator('#typing')).to_have_value('')
            # Real clicks on the isolated in-page Back/Home bar.
            box=web.locator('#qsmart-web-controls').bounding_box()
            web.mouse.click(box['x']+35,box['y']+20)
            expect(web).to_have_url(sample+'/one')
            # Home must close the whole managed web profile while server/launcher survive.
            phone.locator('#btn-home').click()
            expect(phone.locator('#status-text')).to_contain_text('Trang chủ',timeout=12000)
            assert api('/api/status')['brave'] == 'closed'
            assert api('/health')['status'] == 'ok'
            # A fresh web session has no previous website: Back returns to TV.
            assert api('/api/browser/open',{'url':sample+'/one'})['status'] == 'success'
            assert api('/api/control/back',{})['status'] == 'success'
            assert api('/api/status')['brave'] == 'closed'
            phone.screenshot(path=str(settings.DATA_DIR/'logs'/'remote-controls-verified.png'),full_page=True)
            assert not errors,errors
            phone_browser.close()
        print('PASS: automatic URL protocol via API/phone form, LAN QR, one page, popup reuse, Back/Home, native mouse/click/wheel/drag, Unicode live editing, IME, Backspace, focus loss; real Brave.')
    finally:
        server.shutdown()

if __name__ == '__main__':run()
