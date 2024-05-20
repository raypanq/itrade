from typing import Protocol
from websockets import WebSocketClientProtocol

class Streamable(Protocol):
    async def will_connect():
        pass

    async def connected(connection:WebSocketClientProtocol):
        pass

    async def received(connection:WebSocketClientProtocol, jsonstr:str):
        pass

    async def closed(e:Exception):
        pass
    
