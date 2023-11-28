import base64
import json
import logging
import os
import socket
import httptools
from typing import Optional

from utils import HttpResponse

logger = logging.getLogger()


class Client:
    def __init__(self, user_name: str, password: str, server_host="127.0.0.1", server_port=8000) -> None:
        self._user_name = user_name
        self._password = password
        self._server_host = server_host
        self._server_port = server_port
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.connect((server_host, server_port))
        self._sock.settimeout(4)
        self._response = None
        self._request = None
        self._headers = None
        self._result = None

    def _make_headers(self, body: bytes, is_json: bool = True) -> None:
        auth_str = self._user_name + ':' + self._password
        auth = base64.b64encode(auth_str.encode('ascii')).decode()
        head_list = [
            f'Authorization: Basic {auth}',
            f'Host: {self._server_host}:{self._server_port}',
            f'Content-Length: {str(len(body))}',
            'Connection: close',
            'Content-Type: application/octet-stream'
        ]
        if is_json:
            head_list.append('Content-Type: application/json')
            head_list.remove('Content-Type: application/octet-stream')
        self._headers = "\r\n".join(head_list)


    def _send(self) -> None:
        sent = 0
        while sent < len(self._request):
            sent = sent + self._sock.send(self._request[sent:])
        response = b""
        main_data = HttpResponse()
        while True:
            chunk = self._sock.recv(4024)
            p = httptools.HttpResponseParser(main_data)
            p.feed_data(chunk)
            response = response + chunk
            if len(chunk) >= int(main_data.contlength):
                break
        self._response = response
        self._result = main_data.body

    def _make_request(self, body: str, method, path) -> None:
        query = f'{method} /{path} HTTP/1.1\r\n' \
                f'Host:{self._server_host}:{self._server_port}\r\n' \
                f'{self._headers}\r\n\r\n' \
                f'{body}'
        self._request = query.encode()


    def _make_file_request(self, body: bytes, method, path) -> None:
        query = f'{method} /{path} HTTP/1.1\r\n' \
                f'Host:{self._server_host}:{self._server_port}\r\n' \
                f'{self._headers}\r\n\r\n'
        self._request = query.encode() + body


    def send_start(self) -> None:
        logger.info('Get messages/register user')
        body = ""
        self._make_headers(body.encode())
        self._make_request(body, 'POST', 'start')
        self._send()

    def send_message(self, message: str, user: str | None = None) -> None:
        logger.info('Send message')
        if user:
            raw_json = {"text": message, "send_to_public": False, "send_to_user": user}
        else:
            raw_json = {"text": message, "send_to_public": True}
        body = json.dumps(raw_json)
        self._make_headers(body.encode())
        self._make_request(body, 'POST', 'send')
        self._send()

    def comment_message(self, message_id: int, comment: str) -> None:
        logger.info('Comment message')
        raw_json = {"message_id": message_id, "comment": comment}
        body = json.dumps(raw_json)
        self._make_headers(body.encode())
        self._make_request(body, 'POST', 'comment_message')
        self._send()

    def complain(self, username: str) -> None:
        logger.info('Complain to user')
        raw_json = {"username": username}
        body = json.dumps(raw_json)
        self._make_headers(body.encode())
        self._make_request(body, 'POST', 'complain')
        self._send()

    def send_file(self, path_to_file: str, message_id:int) -> None:
        logger.info('Send file')
        isExist = os.path.exists(path_to_file)
        if isExist:
            with open(path_to_file, "rb") as binary_file:
                body = binary_file.read()
            self._make_headers(body, is_json=False)
            self._make_file_request(body, 'POST', f'file?message={message_id}')
            self._send()
        else:
            logger.error('No such file')

    @property
    def response_raw(self) -> bytes:
        return self._response

    @property
    def response(self) -> Optional[dict]:
        return self._result


if __name__ == '__main__':
    client1 = Client(user_name='user1', password='pass')
    client2 = Client(user_name='user2', password='pass')

    client1.send_start()  # регистрация пользователя, если такого не существует, и получение сообщений (последних 20, если новый пользователь или всех непрочитанных, если старый)
    print(client1.response)

    client1.send_message(message='Hello!')  # отправка сообщения в публичный чат
    client1.send_message(message='Hello, user2!', user='user2')  # отправка сообщения пользователю
    client1.comment_message(message_id=1, comment='AZAZA')  # комментарии к сообщению
    client1.complain(username="user2")  # жалоба на пользователя

    with open('testfile', 'a') as f: # создать тестовый файл для отправки
        f.write('test')

    client1.send_file(path_to_file='testfile', message_id=1) # отправка файла

    client2.send_start()
    print(client2.response)
