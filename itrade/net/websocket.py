import asyncio
import websockets
import ssl
from websockets import WebSocketClientProtocol
from . import Streamable

class Websocket:
    def __init__(self, 
                 streamer:Streamable, 
                 auto_reconnect:bool,
                 domain:str,
                 port:int) -> None:
        self._domain = domain
        self._port = port
        self._streamer = streamer
        self._auto_reconnect = auto_reconnect

    def run_loop(self):
        loop = asyncio.get_event_loop()
        # loop.create_task(self._conn_listen())
        loop.run_until_complete(self._connect())
        # loop.run_forever()
        
    async def _connect(self):
        url = f"wss://{self._domain}:{self._port}"
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        while True:
            await self._streamer.will_connect()
            async with websockets.connect(url, ssl=ssl_context, ping_interval=None) as connection:
                await self._streamer.connected(connection)
                try:
                    await self._listen(connection)
                except Exception as e:
                    await self._streamer.closed(e)
                finally:
                    if not self._auto_reconnect:
                        break

    async def _listen(self, ws:WebSocketClientProtocol):
        while True:
            resp_jsonstr = await ws.recv()
            self._streamer.received(resp_jsonstr)
