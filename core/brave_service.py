import asyncio
import json
import logging
import subprocess
import urllib.parse
from pathlib import Path
import httpx
import psutil
from config import settings, BASE_DIR
from core.security import validate_url, normalize_browser_url
from core.process_manager import process_manager
from core.state_manager import state_manager
from core.browser_connection import BrowserConnection
from core.window_manager import wait_for_window_by_pid, force_foreground_window, get_process_family_pids

logger = logging.getLogger('qsmarttv.brave_service')
WORLD = 'QSmartPrivateControls'


class BraveService:
    def __init__(self):
        self._lock = asyncio.Lock()
        self.connection = BrowserConnection()
        self.port = None
        self.target = None
        self.context = None
        self.contexts = set()
        self.dialog_open = False
        self._popup_lock = asyncio.Lock()
        self._handled_popups = set()
        self._reset_history = False
        self._initializing = False

    async def _targets(self):
        async with httpx.AsyncClient(trust_env=False) as client:
            response = await client.get(f'http://127.0.0.1:{self.port}/json/list', timeout=2)
            response.raise_for_status()
            return [t for t in response.json() if t.get('type') == 'page']

    def _port_from_owned_process(self):
        pid = process_manager.get_pid('external_browser')
        if not pid:
            return None
        try:
            port = int((settings.DATA_DIR / 'brave-external-profile' / 'DevToolsActivePort').read_text().splitlines()[0])
            for conn in psutil.Process(pid).net_connections(kind='tcp'):
                if conn.status == psutil.CONN_LISTEN and conn.laddr.port == port and conn.laddr.ip in ('127.0.0.1','::1'):
                    return port
        except (OSError, ValueError, IndexError, psutil.Error):
            pass
        return None

    async def _connect(self):
        if self.connection.connected and process_manager.is_running('external_browser'):
            return
        await self.connection.close()
        self.port = self._port_from_owned_process()
        if not self.port:
            # Upgrade a previously unmanaged TV-browser window using its exact private profile only.
            if process_manager.is_running('external_browser'):
                if not await process_manager.terminate_process('external_browser'):
                    raise RuntimeError('Không đóng được phiên web cũ.')
            if not settings.BRAVE_PATH:
                raise RuntimeError('Không tìm thấy Brave Browser.')
            profile = settings.DATA_DIR / 'brave-external-profile'
            profile.mkdir(parents=True, exist_ok=True)
            (profile / 'DevToolsActivePort').unlink(missing_ok=True)
            proc = subprocess.Popen([settings.BRAVE_PATH, f'--user-data-dir={profile}', '--remote-debugging-address=127.0.0.1',
                '--remote-debugging-port=0', '--no-first-run', '--no-default-browser-check', '--disable-background-mode',
                '--hide-crash-restore-bubble',
                '--start-maximized', '--new-window', 'about:blank'],
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP, close_fds=True)
            process_manager.register_process('external_browser', proc.pid)
            self._reset_history = True
            for _ in range(60):
                self.port = await asyncio.to_thread(self._port_from_owned_process)
                if self.port:
                    break
                await asyncio.sleep(0.1)
            if not self.port:
                raise RuntimeError('Brave chưa sẵn sàng để điều khiển. Kiểm tra đường dẫn và profile.')
        targets = await self._targets()
        if not targets:
            raise RuntimeError('Không tìm thấy trang web. Đóng web TV rồi mở lại.')
        selected = targets[0]
        self.target = selected['id']
        self._handled_popups.clear()
        endpoint = urllib.parse.urlparse(selected['webSocketDebuggerUrl'])
        if endpoint.hostname not in ('127.0.0.1','localhost','::1') or endpoint.port != self.port:
            raise RuntimeError('Địa chỉ điều khiển Brave không thuộc localhost.')
        self._initializing = True
        await self.connection.open(selected['webSocketDebuggerUrl'], self._event)
        await self.connection.command('Page.enable')
        await self.connection.command('Runtime.enable')
        await self.connection.command('Target.setDiscoverTargets', {'discover':True})
        await self.connection.command('Runtime.addBinding', {'name':'qsmartNavigation', 'executionContextName':WORLD})
        source = (BASE_DIR / 'static/input_bridge.js').read_text(encoding='utf-8-sig') + '\n' + (BASE_DIR / 'static/browser_controls.js').read_text(encoding='utf-8-sig')
        await self.connection.command('Page.addScriptToEvaluateOnNewDocument', {'source':source, 'worldName':WORLD})
        tree = await self.connection.command('Page.getFrameTree')
        async def install(frame):
            context = await self.connection.command('Page.createIsolatedWorld', {'frameId':frame['frame']['id'], 'worldName':WORLD})
            context_id = context['executionContextId']
            self.contexts.add(context_id)
            if 'parentId' not in frame['frame']:
                self.context = context_id
            await self.connection.command('Runtime.evaluate', {'expression':source, 'contextId':context_id})
            for child in frame.get('childFrames', []):
                await install(child)
        try:
            await install(tree['frameTree'])
        except RuntimeError as error:
            if 'context' not in str(error).lower() and 'frame' not in str(error).lower():
                raise
            # The initial blank page may finish navigation while attaching. The
            # new-document hook installs the same controls in its replacement.
        for other in targets[1:]:
            try:
                await self.connection.command('Target.closeTarget', {'targetId':other['id']})
            except RuntimeError as error:
                if 'No target with given id' not in str(error):
                    raise
        self._initializing = False

    async def _event(self, event):
        name, data = event['method'], event.get('params', {})
        if name == 'Runtime.executionContextCreated':
            context = data['context']
            if context.get('name') == WORLD:
                self.contexts.add(context['id'])
                if context.get('auxData', {}).get('isDefault') is False:
                    # A focused frame will explicitly identify itself when starting input.
                    self.context = context['id']
        elif name == 'Runtime.executionContextsCleared':
            self.context = None
            self.contexts.clear()
        elif name == 'Runtime.executionContextDestroyed':
            context_id = data.get('executionContextId')
            self.contexts.discard(context_id)
            if self.context == context_id:
                self.context = None
        elif name == 'Page.javascriptDialogOpening':
            self.dialog_open = True
        elif name == 'Page.javascriptDialogClosed':
            self.dialog_open = False
        elif name == 'Runtime.bindingCalled' and data.get('name') == 'qsmartNavigation' and data.get('executionContextId') in self.contexts:
            action = data.get('payload')
            if action in ('back','home'):
                from core.app_controller import app_controller
                await state_manager.update(active_app='browser')
                await (app_controller.handle_back() if action == 'back' else app_controller.handle_home())
        elif name in ('Target.targetInfoChanged','Target.targetCreated'):
            if self._initializing:
                return
            target = data.get('targetInfo', {})
            if target.get('type') == 'page' and target.get('targetId') != self.target:
                url = target.get('url', '')
                if name == 'Target.targetCreated' and url in ('','about:blank'):
                    await asyncio.sleep(0.8)
                    targets = await self._targets()
                    target = next((t for t in targets if t['id'] == target['targetId']), None)
                    if not target:
                        return
                    target['targetId'] = target['id']
                    url = target.get('url','')
                if urllib.parse.urlparse(url).scheme in ('http','https'):
                    async with self._popup_lock:
                        if target['targetId'] in self._handled_popups:
                            return
                        try:
                            await self.connection.command('Page.navigate', {'url':validate_url(url)})
                            self._handled_popups.add(target['targetId'])
                            await self.connection.command('Target.closeTarget', {'targetId':target['targetId']})
                        except RuntimeError:
                            pass
                elif name == 'Target.targetCreated' and url in ('','about:blank'):
                    await self.connection.command('Target.closeTarget', {'targetId':target['targetId']})

    async def open_url(self, url: str, app_name='browser'):
        valid_url = normalize_browser_url(url)
        async with self._lock:
            try:
                await self._connect()
                result = await self.connection.command('Page.navigate', {'url':valid_url})
                if result.get('errorText'):
                    raise RuntimeError('Không truy cập được trang web. Kiểm tra địa chỉ hoặc kết nối mạng.')
                if self._reset_history:
                    await self._ready_command('Page.resetNavigationHistory')
                    self._reset_history = False
                await self._ready_command('Page.bringToFront')
                pid = process_manager.get_pid('external_browser')
                hwnd = await asyncio.to_thread(wait_for_window_by_pid, pid, timeout=3)
                if not hwnd:
                    raise RuntimeError('Không tìm thấy cửa sổ Brave TV.')
                force_foreground_window(hwnd)
                await state_manager.update(active_app=app_name)
                return {'status':'success', 'message':'Đã mở trang trong cửa sổ web TV.'}
            except Exception as error:
                self._initializing = False
                await self.connection.close()
                logger.warning('Không mở được web: %s', type(error).__name__)
                return {'status':'error', 'message':str(error)}

    async def _ready_command(self, method):
        for attempt in range(40):
            try:
                return await self.connection.command(method)
            except RuntimeError as error:
                if 'Not attached to an active page' not in str(error) or attempt == 39:
                    raise
                await asyncio.sleep(0.05)

    async def open_youtube(self, search_query=''):
        url = 'https://www.youtube.com'
        if search_query.strip():
            url += '/results?search_query=' + urllib.parse.quote_plus(search_query.strip())
        return await self.open_url(url, 'youtube')

    async def back(self):
        async with self._lock:
            await self._connect()
            if self.dialog_open:
                await self.connection.command('Page.handleJavaScriptDialog', {'accept':False})
                return True
            modal = await self.connection.command('Runtime.evaluate', {
                'expression':"Array.from(document.querySelectorAll('dialog[open], [role=dialog][aria-modal=true]')).some(el => el.getClientRects().length > 0)",
                'returnByValue':True})
            if modal.get('result', {}).get('value'):
                for kind in ('keyDown','keyUp'):
                    await self.connection.command('Input.dispatchKeyEvent', {'type':kind,'key':'Escape','code':'Escape','windowsVirtualKeyCode':27})
                return True
            history = await self.connection.command('Page.getNavigationHistory')
            previous = history['entries'][:history['currentIndex']]
            previous = [entry for entry in previous if urllib.parse.urlparse(entry['url']).scheme in ('http','https')]
            if not previous:
                return False
            await self.connection.command('Page.navigateToHistoryEntry', {'entryId':previous[-1]['id']})
            return True

    async def input_call(self, method, *args):
        await self._connect()
        if method == 'start':
            await self.connection.command('Page.bringToFront')
        expression = f'QSmartInput.{method}(...{json.dumps(args, ensure_ascii=True)})'
        # Locate the focused editable frame, including same/cross-origin iframes.
        contexts = list(self.contexts)
        if self.context in contexts:
            contexts.remove(self.context)
            contexts.insert(0, self.context)
        last_error = 'Chưa có ô nhập được chọn. Dùng chuột chọn ô rồi thử lại.'
        for context_id in contexts:
            try:
                result = await self.connection.command('Runtime.evaluate', {'expression':expression, 'contextId':context_id, 'returnByValue':True})
            except RuntimeError as error:
                if 'context' not in str(error).lower():
                    raise
                self.contexts.discard(context_id)
                continue
            if not result.get('exceptionDetails'):
                self.context = context_id
                return result.get('result', {}).get('value', {})
            details = result.get('exceptionDetails', {})
            last_error = details.get('exception', {}).get('description', last_error).split('\n')[0]
        raise RuntimeError(last_error)

    async def close_external_browser(self):
        async with self._lock:
            if self.connection.connected:
                try:
                    await self.connection.command('Browser.close', timeout=1)
                except (ConnectionError, RuntimeError, asyncio.TimeoutError):
                    pass
                for _ in range(20):
                    if not process_manager.is_running('external_browser'):
                        break
                    await asyncio.sleep(0.05)
            await self.connection.close()
            self.port = self.target = self.context = None
            self.contexts.clear()
            return await process_manager.terminate_process('external_browser')


brave_service = BraveService()
