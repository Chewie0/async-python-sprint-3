import asyncio
import logging
from protocol import HTTPProtocol
from logging import config
from logging_conf import LOG_CONFIG

logging.config.dictConfig(LOG_CONFIG)
logger = logging.getLogger()


class Server:
    def __init__(self, host: str = '127.0.0.1', port: int = 8000) -> None:
        self._host = host
        self._port = port
        self._server: asyncio | None = None

    async def listen(self) -> None:
        loop = asyncio.get_event_loop()
        self._server = await loop.create_server(HTTPProtocol, self._host, self._port)
        await self._server.serve_forever()

    async def stop(self) -> None:
        self._server.close()
        await self._server.wait_closed()
        self._server = None


if __name__ == '__main__':
    server = Server()
    asyncio.run(server.listen())
