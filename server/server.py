import socket
import threading
import logging
import time
from typing import Set
from shared.message import Message, MessageTypeEnum

# Create a logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Configure the logger
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)


class Client:
    def __init__(
        self, socket: socket.socket, address: tuple, client_list: "ClientList"
    ):
        """
        Initialize a new client connection.

        Args:
            - `socket` (socket.socket): The client socket.
            - `address` (tuple): The client's address (IP, port).
            - `client_list` (ClientList): The list of connected clients.
        """
        self.socket = socket
        self.address = address
        self.client_list = client_list

    def handle(self) -> None:
        """
        Handle communication with a connected client.
        """
        client_ip = self.address[0]
        logger.info(f"A new client connects from {client_ip}")

        self.client_list.add_client(self)
        self.client_list.update_clients()

        while True:
            time.sleep(1)
            try:
                data = self.socket.recv(2065)
                if not data:
                    continue  # Continue listening even if there is no data

                logger.info(f"Received from {client_ip}: {data.decode('utf-8')}")
            except Exception as err:
                logger.error(err)
                logger.info("Removing client due to network error")
                self.client_list.remove_client(self)
                self.client_list.update_clients()
                logger.info(f"Client successfully disconnected from {client_ip}")


class ClientList:
    def __init__(self):
        """
        Initialize a list to keep track of connected clients.
        """
        self.clients: Set[Client] = set()

    def add_client(self, client: Client) -> None:
        """
        Add a client's IP address to the list of connected clients.

        Args:
            - `client` (Client): The client
        """
        self.clients.add(client)

    def remove_client(self, client: Client) -> None:
        """
        Remove a client's IP address from the list of connected clients.

        Args:
            - `client` (Client): The client
        """
        self.clients.remove(client)

    def update_clients(self) -> None:
        """
        Send an updated client list to all connected clients.
        """
        client_list = ",".join([client.address[0] for client in self.clients])
        message = Message(type=MessageTypeEnum.CLIENT_LIST_UPDATE, message=client_list)
        for client in self.clients:
            client.socket.send(message.dump())
        logger.info("Client list sent to all connected clients")


class Server:
    def __init__(self, host: str, port: int):
        """
        Initialize a server to manage client connections.

        Args:
            - `host` (str): The server's host address.
            - `port` (int): The server's port number.
        """
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_list = ClientList()

    def start(self) -> None:
        """
        Start the server and handle incoming client connections.
        """
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        logger.info(f"Server running on {self.host}:{self.port}")

        while True:
            client_socket, client_addr = self.server_socket.accept()
            client = Client(client_socket, client_addr, self.client_list)
            client_handler = threading.Thread(target=client.handle)
            client_handler.start()
