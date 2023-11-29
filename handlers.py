import logging
import uuid
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs
from typing import Callable, TypeVar, ParamSpec
from sqlalchemy import desc
from sqlalchemy.exc import DatabaseError
from sqlalchemy.orm import Session
from sqlalchemy_file.exceptions import SizeValidationError
from models import Chat, Chat_user, Message, User, PUBLIC_CHAT, PUBLIC_CHAT_ID, Comment, Attachment, engine
from utils import get_or_create, ResponseCustom, HttpResponse
from settings import LAST_MESSAGE_COUNT, LIMIT_FOR_BUNNED, HOUR_FOR_BUNNED, RESP_CODE, T, P

logger = logging.getLogger()


class Handler:
    objects = {}

    @classmethod
    def register(cls, command: str) -> Callable[P, T]:
        def decorator(func):
            cls.objects[command] = func
            return func

        return decorator

    @classmethod
    def handle(cls, main_data: HttpResponse) -> str:
        parse_url = urlparse(main_data.url)
        if parse_url.path not in cls.objects:
            logger.error(f'Unknown command "{main_data.url}"')
        logger.info(f'Get method "{main_data.url}"')
        handler = cls.objects[parse_url.path]
        answer = handler(main_data)
        return answer

    @classmethod
    def all(cls) -> list[callable]:
        return list(cls.objects.values())

    @classmethod
    def check_auth(cls, creds: str) -> User | None:
        try:
            with Session(engine) as session:
                user = session.query(User).filter_by(login=creds.split(':')[0],
                                                     password=creds.split(':')[1]).one_or_none()
                if user.id:
                    return user
                else:
                    return None
        except DatabaseError:
            logger.error('Database error')
            return None

    @classmethod
    def get_messages_dict(cls, chat_name: str, messages: list) -> dict:
        tmp_dict = {}
        tmp_dict[chat_name] = [
            {'id': message.id,
             'from': message.author.login,
             'text': message.text,
             'date': str(message.pub_date),
             'comments': [c.text for c in message.comments],
             'attachments': [c.id for c in message.attachments]
             }
            for message in messages]
        return tmp_dict


@Handler.register('start')
def start(data: HttpResponse) -> str:
    try:
        username = data.auth_data.split(':')[0]
        password = data.auth_data.split(':')[1]
        with Session(engine) as session:
            public_chat, _ = get_or_create(session, Chat, name=PUBLIC_CHAT)
            user_obj, is_new = get_or_create(session, User, login=username)
            tmp_dict = {}
            if is_new:
                logger.info(f"New user {data.auth_data.split(':')[0]}")
                get_or_create(session, Chat_user, chat_id=public_chat.id, user_id=user_obj.id)
                user_obj.password = password
                last_messages = session.query(Message).filter(Message.chat_id == public_chat.id).order_by(
                    desc(Message.pub_date)).limit(LAST_MESSAGE_COUNT).all()
                tmp_dict.update(Handler.get_messages_dict(public_chat.name, last_messages))
            else:
                logger.info(f"Start user {data.auth_data.split(':')[0]}")
                user_obj_auth = Handler.check_auth(data.auth_data)
                if user_obj_auth:
                    last_connection = user_obj.last_connection
                    user_chats = session.query(Chat_user).filter(Chat_user.user_id == user_obj.id).all()
                    for chat in user_chats:
                        unread_messages = session.query(Message).filter(Message.chat_id == chat.chat_id,
                                                                        Message.pub_date > last_connection).all()
                        chat_obj = session.query(Chat).filter(Chat.id == chat.chat_id).first()
                        tmp_dict.update(Handler.get_messages_dict(chat_obj.name, unread_messages))
                else:
                    resp = ResponseCustom(resp_status=RESP_CODE['unauth'], resp_status_text='UNAUTHORIZED ',
                                          resp_body={})
                    return resp.get_resp
            user_obj.last_connection = datetime.utcnow()
            session.commit()
        resp = ResponseCustom(resp_status=RESP_CODE['ok'], resp_status_text='OK', resp_body=tmp_dict)
    except Exception as e:
        logger.error(f'ERROR {e}')
        resp = ResponseCustom(resp_status=RESP_CODE['err'], resp_status_text='Bad request', resp_body={})
    return resp.get_resp


@Handler.register('send')
def send(data: HttpResponse) -> str:
    user_obj = Handler.check_auth(data.auth_data)
    if user_obj.id:
        with Session(engine) as session:
            to_public = data.body.get("send_to_public")
            recipient_name = data.body.get("send_to_user")
            if user_obj.banned_till is None or user_obj.banned_till < datetime.utcnow():
                if to_public:
                    message = Message(text=data.body.get("text"), author_id=user_obj.id, chat_id=PUBLIC_CHAT_ID)
                    session.add(message)
                    session.commit()
                    resp = ResponseCustom(resp_status=RESP_CODE['created'], resp_status_text='Created', resp_body={})
                elif not to_public and recipient_name:
                    recipient_obj = session.query(User).filter_by(login=recipient_name).first()
                    if not recipient_obj:
                        resp = ResponseCustom(resp_status=RESP_CODE['err'], resp_status_text='No such user',
                                              resp_body={})
                        return resp.get_resp
                    get_private_chat = session.query(Chat).filter(Chat.name != PUBLIC_CHAT,
                                                                  Chat.user.any(login=user_obj.login),
                                                                  Chat.user.any(login=recipient_obj.login)).first()
                    if not get_private_chat:
                        new_chat = Chat(name=f'Private_chat-{user_obj.id}-{recipient_obj.id}')
                        new_chat.user = [user_obj, recipient_obj]
                        session.add(new_chat)
                        session.commit()
                        id_chat_to_send = new_chat.id
                    else:
                        id_chat_to_send = get_private_chat.id
                    message = Message(text=data.body.get("text"), author_id=user_obj.id, chat_id=id_chat_to_send)
                    session.add(message)
                    session.commit()
                    resp = ResponseCustom(resp_status=RESP_CODE['created'], resp_status_text='Created', resp_body={})
            else:
                resp = ResponseCustom(resp_status=RESP_CODE['err'], resp_status_text='User is bunned', resp_body={})
    else:
        resp = ResponseCustom(resp_status=RESP_CODE['unauth'], resp_status_text='UNAUTHORIZED ',
                              resp_body={})
    return resp.get_resp


@Handler.register('complain')
def complain_on_user(data: HttpResponse) -> str:
    user_obj = Handler.check_auth(data.auth_data)
    if user_obj.id:
        with Session(engine) as session:
            user_to_complain = session.query(User).filter_by(login=data.body.get("username")).first()
            user_to_complain.count_for_banned += 1
            if user_to_complain.count_for_banned >= LIMIT_FOR_BUNNED:
                user_to_complain.banned_till = datetime.utcnow() + timedelta(hours=HOUR_FOR_BUNNED)
                user_to_complain.count_for_banned = 0
            session.commit()
        resp = ResponseCustom(resp_status=RESP_CODE['created'], resp_status_text='Created', resp_body={})
    else:
        resp = ResponseCustom(resp_status=RESP_CODE['unauth'], resp_status_text='UNAUTHORIZED ',
                              resp_body={})
    return resp.get_resp


@Handler.register('comment_message')
def comment_message(data: HttpResponse) -> str:
    user_obj = Handler.check_auth(data.auth_data)
    if user_obj.id:
        with Session(engine) as session:
            message = session.query(Message).filter_by(id=data.body.get("message_id")).first()
            if message:
                comment = Comment(author_id=user_obj.id, message_id=message.id, text=data.body.get("comment"))
                session.add(comment)
                session.commit()
                logger.info('Comment have created')
            else:
                resp = ResponseCustom(resp_status=RESP_CODE['err'], resp_status_text='No such message', resp_body={})
                return resp.get_resp
        resp = ResponseCustom(resp_status=RESP_CODE['created'], resp_status_text='Created', resp_body={})
    else:
        resp = ResponseCustom(resp_status=RESP_CODE['unauth'], resp_status_text='UNAUTHORIZED ',
                              resp_body={})
    return resp.get_resp


@Handler.register('file')
def send_file(data: HttpResponse) -> str:
    user_obj = Handler.check_auth(data.auth_data)
    if user_obj.id:
        parse_url = urlparse(data.url)
        p = parse_qs(parse_url.query)
        message_id = p.get('message')[0]
        if message_id:
            try:
                with Session(engine) as session:
                    file_uid = uuid.uuid4()
                    att = Attachment(name=f"attachment_{user_obj.id}_{message_id}_{file_uid}", content=data.body,
                                     message_id=message_id)
                    session.add(att)
                    session.commit()
                resp = ResponseCustom(resp_status=RESP_CODE['created'], resp_status_text='Created', resp_body={})
            except SizeValidationError:
                resp = ResponseCustom(resp_status=RESP_CODE['err'], resp_status_text='Too big file', resp_body={})
            return resp.get_resp
    else:
        resp = ResponseCustom(resp_status=RESP_CODE['unauth'], resp_status_text='UNAUTHORIZED ',
                              resp_body={})
        return resp.get_resp
