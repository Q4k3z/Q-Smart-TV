"""Opt-in real browser check: start Q Smart TV first, then run this script.

Uses installed Brave and exercises the actual launcher API. No browser download.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from playwright.sync_api import sync_playwright, expect
from config import settings
import urllib.request
import json

BASE = f'http://127.0.0.1:{settings.PORT}'


def api(path, method='GET'):
    req = urllib.request.Request(BASE + path, method=method, headers={'Authorization': f'Bearer {settings.AUTH_TOKEN}'})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.load(resp)


def run():
    assert settings.BRAVE_PATH, 'Brave is required for this real browser test.'
    assert api('/api/launcher/open', 'POST')['status'] in ('success', 'already_running')
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=settings.BRAVE_PATH, headless=True)
        context = browser.new_context(viewport={'width':1920, 'height':1080})
        errors = []
        tv = context.new_page()
        tv.on('pageerror', lambda err: errors.append(str(err)))
        tv.goto(f'{BASE}/tv?token={settings.AUTH_TOKEN}')
        expect(tv.locator('[data-app=youtube]')).to_be_focused()
        expect(tv.locator('#remote-ip-info')).to_contain_text('Server online')
        assert 'token=' not in tv.url
        remote = context.new_page()
        remote.on('pageerror', lambda err: errors.append(str(err)))
        remote.goto(f'{BASE}/remote?token={settings.AUTH_TOKEN}')
        expect(remote.locator('#status-text')).to_contain_text('TV đang mở')
        assert 'token=' not in remote.url
        remote.locator('#btn-right').click()
        expect(tv.locator('[data-app=browser]')).to_be_focused()
        remote.locator('#btn-ok').click()
        expect(tv.locator('#browser-input')).to_be_visible()
        tv.locator('#browser-input').fill(BASE.removeprefix('http://')+'/health')
        with tv.expect_response('**/api/browser/open') as opened:
            tv.locator('#browser-input').press('Enter')
        assert opened.value.status == 200 and opened.value.json()['status'] == 'success'
        remote.locator('#btn-home').click()
        expect(tv.locator('[data-app=youtube]')).to_be_focused()
        expect(tv.locator('#content-view')).to_contain_text('Chào mừng')
        tv.locator('#qr-pairing-btn').click()
        expect(tv.locator('#qr-modal')).to_have_class('modal-overlay active')
        tv.keyboard.press('Escape')
        expect(tv.locator('#qr-pairing-btn')).to_be_focused()
        for width in (1280, 720):
            tv.set_viewport_size({'width':width, 'height':900})
            tv.locator('[data-app=youtube]').focus()
            tv.keyboard.press('ArrowDown')
            assert tv.locator(':focus').count() == 1
            assert tv.locator(':focus').get_attribute('data-app') != 'youtube'
        remote.locator('#btn-exit-tv').click()
        expect(remote.locator('#exit-modal')).to_have_class('modal-overlay active')
        remote.locator('#modal-btn-cancel').click()
        assert api('/api/status')['launcher'] == 'open'
        remote.locator('#btn-exit-tv').click()
        remote.locator('#modal-btn-confirm').click()
        expect(remote.locator('#reopen-card')).to_have_class('reopen-card visible')
        assert api('/api/status')['launcher'] == 'closed'
        assert api('/health')['status'] == 'ok'
        remote.locator('#btn-reopen-tv').click()
        expect(remote.locator('#status-text')).to_contain_text('TV đang mở', timeout=15000)
        assert api('/api/status')['launcher'] == 'open'
        # Business errors returned as HTTP 200 must still be visible to the user.
        remote.route('**/api/launcher/open', lambda route: route.fulfill(json={'status':'error', 'message':'Lỗi kiểm thử có chủ đích'}))
        remote.locator('#reopen-card').evaluate("el => el.classList.add('visible')")
        remote.locator('#btn-reopen-tv').click()
        expect(remote.locator('#alert-banner')).to_have_text('Lỗi kiểm thử có chủ đích')
        remote.unroute('**/api/launcher/open')
        remote.evaluate('fetchStatus()')
        expect(remote.locator('#reopen-card')).not_to_have_class('reopen-card visible')
        remote.locator('#alert-banner').evaluate("el => el.className = 'alert-banner'")
        tv.set_viewport_size({'width':1920, 'height':1080})
        tv.locator('[data-app=youtube]').focus()
        screenshots = settings.DATA_DIR / 'logs'
        tv.screenshot(path=str(screenshots / 'tv-verified.png'))
        remote.set_viewport_size({'width':390, 'height':844})
        remote.screenshot(path=str(screenshots / 'remote-verified.png'), full_page=True)
        assert not errors, errors
        browser.close()
    print('PASS: Brave UI, D-pad, Home, QR/Back, responsive focus, cancel/exit/reopen, server survival, error display; no JS errors.')


if __name__ == '__main__':
    run()
