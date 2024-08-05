import asyncio
import logging
import socket
from asyncio import AbstractEventLoop


class CygSocketServerAsyncio:

    clients = dict()  # 保存已连接的client
    tasks = dict()
    loop: AbstractEventLoop = None

    def __init__(self, address="127.0.01", port=8000):
        self._address = address
        self._port = port
        self._logger = logging.getLogger(f"{self.__module__}.{self.__class__.__name__}")

    @property
    def logger(self):
        return self._logger

    def operations_return_data(self, data):
        self._logger.warning(f"*** 回显 *** -> 没有重写 operations_return_data 函数, 默认是回显.")
        return data

    async def socket_send(self, client_connection, data: bytes):
        """发送数据给客户端."""
        if client_connection:
            client_ip = client_connection.getpeername()
            await self.loop.sock_sendall(client_connection, data)
            self._logger.info(f"***发送*** --> {client_ip} 发送成功, {data}")
        else:
            self._logger.info(f"***发送*** --> 发送失败, {data}, 未连接")

    async def receive_send(self, client_connection: socket.socket):
        client_ip = client_connection.getpeername()[0]  # 获取连接客户端的ip
        try:
            while data := await self.loop.sock_recv(client_connection, 1024 * 1024):
                self._logger.info(f"{ '-' * 60}")
                self._logger.info(f"***Socket接收*** --> {client_ip}, 数据: {data}")
                send_data = self.operations_return_data(data) + b"\r\n"  # 这个方法实现具体业务, 需要重写, 不重写回显
                await self.loop.sock_sendall(client_connection, send_data)
                self._logger.info(f"***Socket回复*** --> {client_ip}, 数据: {send_data}")
                self._logger.info(f"{ '-' * 60}")
        except Exception as e:
            self._logger.warning(f"***通讯出现异常*** --> 异常信息是: {e}")
        finally:
            self.clients.pop(client_ip)
            self.tasks.get(client_ip).cancel()
            self._logger.warning(f"***下位机断开*** --> {client_ip}, 断开了")
            client_connection.close()

    async def listen_for_connection(self, socket_server: socket):
        while True:
            self.loop = asyncio.get_running_loop()
            client_connection, address = await self.loop.sock_accept(socket_server)
            client_connection.setblocking(False)
            self.clients.update({address[0]: client_connection})
            self.tasks.update({address[0]: self.loop.create_task(self.receive_send(client_connection))})
            self._logger.warning(f"***下位机连接*** --> {address}, 连接了")

    async def run_socket_server(self):
        """运行socket服务, 并监听客户端连接."""
        socket_server = socket.socket()
        socket_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        socket_server.setblocking(False)
        socket_server.bind((self._address, self._port))
        socket_server.listen()
        await self.listen_for_connection(socket_server)


if __name__ == '__main__':
    log_format = "%(asctime)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s"
    logging.basicConfig(level=logging.INFO, encoding="UTF-8", format=log_format)
    cyg_socket_server = CygSocketServerAsyncio("127.0.0.1", 8000)
    asyncio.run(cyg_socket_server.run_socket_server())
