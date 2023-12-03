import os
from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
from sqlalchemy.sql import func
from sqlalchemy_file import FileField
from sqlalchemy_file.validators import SizeValidator
from sqlalchemy_file.storage import StorageManager
from libcloud.storage.drivers.local import LocalStorageDriver
from settings import basedir, MAX_FILE_SIZE

engine = create_engine('sqlite:///' + os.path.join(basedir, 'data.sqlite'), echo=True)
Base = declarative_base()
os.makedirs("./upload_dir/attachment", 0o777, exist_ok=True)
container = LocalStorageDriver("./upload_dir").get_container("attachment")
StorageManager.add_storage("default", container)


class Chat_user(Base):
    __tablename__ = 'chat_user'
    chat_id = Column(Integer, ForeignKey('chat.id'), primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), primary_key=True)


class Message(Base):
    __tablename__ = 'message'
    id = Column(Integer, primary_key=True)
    text = Column(String(500), nullable=False)
    chat_id = Column(Integer, ForeignKey("chat.id"))
    pub_date = Column(DateTime(timezone=True), server_default=func.now())
    author_id = Column(Integer, ForeignKey('user.id'))
    comments = relationship('Comment', backref='message', cascade="all, delete")
    attachments = relationship("Attachment", backref='message', cascade="all, delete")


class Attachment(Base):
    __tablename__ = "attachment"
    id = Column(Integer, autoincrement=True, primary_key=True)
    name = Column(String(150), unique=True)
    content = Column(FileField(validators=[SizeValidator(max_size=MAX_FILE_SIZE)]))
    message_id = Column(Integer, ForeignKey('message.id'))


class Comment(Base):
    __tablename__ = 'comments'
    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(Integer, ForeignKey('message.id'))
    author_id = Column(Integer, ForeignKey('user.id'))
    text = Column(Text(length=255), nullable=False)
    created = Column(DateTime(timezone=True), server_default=func.now())


class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True, autoincrement=True)
    login = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=True)
    messages = relationship("Message", backref='author')
    chat = relationship('Chat', secondary='chat_user', back_populates='user')
    last_connection = Column(DateTime(timezone=True))
    count_for_banned = Column(Integer, default=0)
    banned_till = Column(DateTime(timezone=True), nullable=True)

    def __str__(self):
        return self.id


class Chat(Base):
    __tablename__ = 'chat'
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    messages = relationship("Message", lazy='dynamic')
    user = relationship("User", secondary='chat_user', lazy='dynamic', back_populates='chat')
