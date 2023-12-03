from sqlalchemy.orm import Session
from settings import PUBLIC_CHAT, PUBLIC_CHAT_ID
from models import Chat, Base, engine


def main():
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        public_chat = Chat(
            id=PUBLIC_CHAT_ID,
            name=PUBLIC_CHAT,
        )
        session.add(public_chat)
        session.commit()


if __name__ == '__main__':
    main()
