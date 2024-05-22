from typing import Protocol
from websockets import WebSocketClientProtocol

class Streamable(Protocol):
    @staticmethod
    async def will_connect():
        pass

    @staticmethod
    async def connected(connection:WebSocketClientProtocol):
        pass

    @staticmethod
    async def received(connection:WebSocketClientProtocol, jsonstr:str):
        pass

    @staticmethod
    async def closed(e:Exception):
        pass
    
