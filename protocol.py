import asyncio
import logging
import httptools
from handlers import Handler
from utils import HttpResponse

logger = logging.getLogger()


class HTTPProtocol(asyncio.Protocol):

    def connection_made(self, transport: asyncio.Transport) -> None:
        self.transport = transport
        addr = transport.get_extra_info('peername')
        logger.info('Connection from {}'.format(addr))

    def data_received(self, data: bytes) -> None:
        main_data = HttpResponse()
        p = httptools.HttpRequestParser(main_data)
        p.feed_data(data)
        method = p.get_method().decode()
        logger.info(f"Request: {method} {main_data} ")
        self._handle_data(method, main_data)

    def _handle_data(self, method: str, main_data: HttpResponse) -> None:
        if method == "GET" and main_data.url == 'exit':
            logger.info(f"Close connection")
            self.transport.close()
        elif method == "POST":
            resp = Handler.handle(main_data)
            self.transport.write(resp.encode())
        else:
            self.transport.write(b"HTTP/1.1 404 Not Found\r\n\r\n")
            self.transport.close()
            logger.info(f"Close connection")

    def connection_lost(self, exception) -> None:
        logging.info('Connection_lost')
        super().connection_lost(exception)

    def eof_received(self) -> None:
        logging.info('EOF received')
        self.transport.close()


