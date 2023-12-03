from client import Client
from utils import logger


def main():
    client1 = Client(user_name='user1', password='pass')
    client2 = Client(user_name='user2', password='pass')

    client1.first_start()  # регистрация пользователя и получение сообщений (последних 20 из публичного чата)
    client1.send_message(message='Hello!')  # отправка сообщения в публичный чат

    client2.first_start()
    logger.info(client2.response)  # получение ответа

    client1.send_message(message='Hello again!')
    client1.send_message(message='Hello, user2!', user='user2')  # отправка сообщения пользователю
    client1.comment_message(message_id=2, comment='AZAZA')  # комментарии к сообщению'''
    client1.complain(username="user2")  # жалоба на пользователя

    with open('testfile', 'a') as f:  # создать тестовый файл для отправки
        f.write('test')

    client1.send_file(path_to_file='testfile', message_id=2)  # отправка файла

    client2.get_messages() # получение непрочитанных сообщений
    logger.info(client2.response)


if __name__ == '__main__':
    main()
