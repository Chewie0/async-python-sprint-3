import asyncio
from protocol import HTTPProtocol
from utils import logger


class Server:
    def __init__(self, host: str = '127.0.0.1', port: int = 8000) -> None:
        self._host = host
        self._port = port
        self._server: asyncio.AbstractServer | None = None

    async def listen(self) -> None:
        loop = asyncio.get_event_loop()
        self._server = await loop.create_server(HTTPProtocol, self._host, self._port)
        async with self._server:
            try:
                logger.info("Server start")
                await self._server.serve_forever()
            except asyncio.exceptions.CancelledError:
                logger.info("Server stop")

    async def stop(self) -> None:
        self._server.close()
        await self._server.wait_closed()
        self._server = None


if __name__ == '__main__':
    server = Server()
    asyncio.run(server.listen())
