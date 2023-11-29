import os
from typing import TypeVar, ParamSpec

basedir = os.path.abspath(os.path.dirname(__file__))
PUBLIC_CHAT = 'Public_chat'
PUBLIC_CHAT_ID = 1
MAX_FILE_SIZE = '5M'

T = TypeVar('T')
P = ParamSpec('P')
LAST_MESSAGE_COUNT = 20
LIMIT_FOR_BUNNED = 3
HOUR_FOR_BUNNED = 4
RESP_CODE = {'ok': 200,
             'created': 201,
             'err': 400,
             'unauth': 401,
             'not_found': 404}
