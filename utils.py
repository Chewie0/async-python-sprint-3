import base64
import json
import logging
from logging import config
from dataclasses import dataclass
from logging_conf import LOG_CONFIG

logging.config.dictConfig(LOG_CONFIG)
logger = logging.getLogger()


@dataclass
class ResponseCustom:
    resp_status: int
    resp_status_text: str
    resp_body: dict

    @property
    def get_resp(self):
        return f'HTTP/1.1 {self.resp_status} {self.resp_status_text}\r\n' \
               'Content-Type: application/json; charset=UTF-8\r\n' \
               f'Content-Length: {str(len(json.dumps(self.resp_body)))}\r\n' \
               '\r\n' \
               f'{json.dumps(self.resp_body)}'


class HttpResponse:
    def __init__(self):
        self.body = None
        self.url = None
        self.status = None
        self.auth_data = None
        self.contenttype = None
        self.contlength = 0

    def on_url(self, url: bytes):
        self.url = url.decode().replace('/', '')

    def on_status(self, status: bytes):
        self.status = status.decode()

    def on_header(self, name: bytes, value: bytes):
        if name == b'Content-Type':
            val = value.decode("ISO-8859-1").split(' ')[0]
            self.contenttype = val
        if name == b'Content-Length':
            val = value.decode("ISO-8859-1").split(' ')[0]
            self.contlength = val
        if name == b'Authorization':
            val = value.decode("ISO-8859-1").split(' ')[1]
            self.auth_data = base64.b64decode(val).decode("UTF-8")

    def on_body(self, body: bytes):
        if 'application/json' not in self.contenttype:
            self.body = body
        else:
            self.body = json.loads(body.decode())

    def __str__(self):
        return f"{self.url}"


def get_or_create(session, model, defaults=None, **kwargs):
    instance = session.query(model).filter_by(**kwargs).one_or_none()
    if instance:
        return instance, False
    else:
        kwargs |= defaults or {}
        instance = model(**kwargs)
        try:
            session.add(instance)
            session.commit()
        except Exception:
            session.rollback()
            instance = session.query(model).filter_by(**kwargs).first()
            return instance, False
        else:
            return instance, True
