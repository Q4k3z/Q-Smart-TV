"""Small CDP transport to our private Brave profile, on loopback only."""
import asyncio
import json
import logging
from websockets.asyncio.client import connect

logger = logging.getLogger('qsmarttv.browser_connection')


class BrowserConnection:
    def __init__(self):
        self.socket = None
        self.reader = None
        self.pending = {}
        self.serial = 0
        self.tasks = set()
        self.handler = None

    @property
    def connected(self):
        return self.reader is not None and not self.reader.done()

    async def open(self, url, handler):
        self.handler = handler
        self.socket = await connect(url, open_timeout=3, max_size=2**20, proxy=None)
        self.reader = asyncio.create_task(self._read())

    async def command(self, method, params=None, timeout=4):
        if not self.connected:
            raise ConnectionError('Brave chưa kết nối.')
        self.serial += 1
        request_id = self.serial
        future = asyncio.get_running_loop().create_future()
        self.pending[request_id] = (future, method)
        try:
            await self.socket.send(json.dumps({'id': request_id, 'method': method, 'params': params or {}}))
            return await asyncio.wait_for(future, timeout)
        finally:
            self.pending.pop(request_id, None)

    async def _event(self, message):
        try:
            await self.handler(message)
        except (ConnectionError, asyncio.TimeoutError):
            pass
        except Exception as error:
            logger.warning('Browser event failed: %s', str(error)[:200])

    async def _read(self):
        try:
            async for raw in self.socket:
                message = json.loads(raw)
                entry = self.pending.get(message.get('id'))
                future, method = entry if entry else (None, None)
                if future and not future.done():
                    if 'error' in message:
                        future.set_exception(RuntimeError(f"{method}: {message['error'].get('message', 'Browser error')}"))
                    else:
                        future.set_result(message.get('result', {}))
                elif 'method' in message:
                    task = asyncio.create_task(self._event(message))
                    self.tasks.add(task)
                    task.add_done_callback(self.tasks.discard)
        except Exception:
            pass
        finally:
            for future, method in tuple(self.pending.values()):
                if not future.done():
                    future.set_exception(ConnectionError('Kết nối Brave đã đóng.'))

    async def close(self):
        if self.socket:
            await self.socket.close()
        current = asyncio.current_task()
        for task in tuple(self.tasks):
            if task is not current:
                task.cancel()
        if self.reader and self.reader is not current:
            await asyncio.gather(self.reader, return_exceptions=True)
        self.reader = None
