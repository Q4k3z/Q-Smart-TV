"""Opt-in live YouTube input check; requires Internet and installed Brave.

Does not submit a search, sign in, or play a video. Uses only managed profiles.
"""
import sys
import json
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from playwright.sync_api import sync_playwright, expect
from config import settings

BASE = f'http://127.0.0.1:{settings.PORT}'


def api(path, body):
    request = urllib.request.Request(BASE + path, data=json.dumps(body).encode(),
        headers={'Authorization': f'Bearer {settings.AUTH_TOKEN}', 'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=25) as response:
        result = json.load(response)
    assert result['status'] == 'success', result.get('message', 'Request failed')
    return result


def run():
    try:
        api('/api/control/home', {})
        api('/api/browser/youtube', {})
        port = int((settings.DATA_DIR/'brave-external-profile'/'DevToolsActivePort').read_text().splitlines()[0])
        with sync_playwright() as p:
            managed = p.chromium.connect_over_cdp(f'http://127.0.0.1:{port}')
            web = managed.contexts[0].pages[0]
            search = web.locator('input[name=search_query]').first
            expect(search).to_be_visible(timeout=30000)
            expect(web.locator('#qsmart-web-controls')).to_be_attached()
            phone_browser = p.chromium.launch(executable_path=settings.BRAVE_PATH, headless=True)
            phone = phone_browser.new_page(viewport={'width':390, 'height':844}, is_mobile=True, has_touch=True)
            phone.goto(BASE+'/remote?token='+settings.AUTH_TOKEN)
            expect(phone.locator('#control-target')).to_contain_text('YouTube')
            phone.wait_for_function('ws?.readyState === WebSocket.OPEN')
            search.click()
            phone.locator('#mode-keyboard').click()
            phone.locator('#input-start').click()
            expect(phone.locator('#live-text')).to_be_enabled()
            phone.locator('#live-text').fill('Q Smart TV tiếng Việt')
            try:
                expect(search).to_have_value('Q Smart TV tiếng Việt')
            except AssertionError as error:
                details = web.evaluate("({focused:document.hasFocus(),active:document.activeElement?.tagName,value:document.activeElement?.value})")
                raise AssertionError(f"{phone.locator('#typing-status').inner_text()}; {details}") from error
            phone.locator('#live-text').fill('Q Smart TV đã sửa')
            expect(search).to_have_value('Q Smart TV đã sửa')
            phone.locator('#live-text').fill('')
            expect(search).to_have_value('')
            phone_browser.close()
        print('PASS: live YouTube search field, private toolbar, native Vietnamese typing/edit/delete; no search submitted.')
    finally:
        api('/api/control/home', {})


if __name__ == '__main__':
    run()
