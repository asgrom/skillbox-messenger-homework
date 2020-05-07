"""
Серверное приложение для соединений
"""
import asyncio
from asyncio import transports


class ClientProtocol(asyncio.Protocol):
    login: str
    server: 'Server'
    transport: transports.Transport

    def __init__(self, server: 'Server'):
        self.server = server
        self.login = None

    def data_received(self, data: bytes):
        decoded = data.decode()
        print(decoded)

        if self.login is None:
            # login:User
            if decoded.startswith("login:"):
                login = decoded.replace("login:", "").strip()

                # вызываем метод проверки логина
                if not self.check_login(login):
                    return

                self.transport.write(
                    f"Привет, {self.login}!\n".encode()
                )

                # посылаем историю чата
                self.send_history()
        else:
            self.send_message(decoded)

    def send_message(self, message):
        format_string = f"<{self.login}> {message}"
        encoded = format_string.encode()

        for client in self.server.clients:
            if client.login != self.login:
                client.transport.write(encoded)

        # добавляем сообщение в историю
        self.server.add_msg_to_history(format_string)

    def connection_made(self, transport: transports.Transport):
        self.transport = transport
        self.server.clients.append(self)
        print("Соединение установлено")

    def connection_lost(self, exception):
        self.server.clients.remove(self)
        print("Соединение разорвано")

    def check_login(self, login):
        """Проверка логина

        Если логин существует, закрываем соединение с пользователем.
        """
        for client in self.server.clients:
            if login == client.login:
                self.transport.write('Логин {{{0}}} занят, попробуйте другой.'.format(login).encode())
                self.transport.close()
                return False
        self.login = login
        return True

    def send_history(self, count=10):
        """Посылает историю чата пользователю

        Количество сообщений чата задается аргументом count(по-умолчанию 10)
        """
        len_history = len(self.server.history)

        if len_history > count:
            messages = '\n'.join(self.server.history[len_history - count:])
        else:
            messages = '\n'.join(self.server.history[:])
            
        messages = 'Последние сообщения в чате:\n' + messages
        self.transport.write(messages.encode())


class Server:
    clients: list
    history: list

    def __init__(self):
        self.clients = []
        self.history = []

        # макс. кол-во сообщений в истории
        self.max_history = 20

    def create_protocol(self):
        return ClientProtocol(self)

    def add_msg_to_history(self, msg):
        """Добавляет сообщение в конец истории

        Если история достигла максимума, удаляется первое сообщение.
        """
        if len(self.history) > self.max_history:
            self.history.pop(0)
        self.history.append(msg)

    async def start(self):
        loop = asyncio.get_running_loop()

        coroutine = await loop.create_server(
            self.create_protocol,
            "127.0.0.1",
            8888
        )

        print("Сервер запущен ...")

        await coroutine.serve_forever()


process = Server()
try:
    asyncio.run(process.start())
except KeyboardInterrupt:
    print("Сервер остановлен вручную")
