import json
import socket
import threading
import logging
import time
from typing import Set
import uuid
from shared.message import Message, MessageTypeEnum

# Create a logger
logger = logging.getLogger(__name__)
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
        self.uuid = str(uuid.uuid4())
        self.alias = ""
        self.socket = socket
        self.address = address
        self.client_list = client_list

    def handle(self) -> None:
        """
        Handle communication with a connected client.
        """
        client_ip = self.address[0]
        logger.info(f"A new client connects from {client_ip}")

        uuid_message = Message(
            type=MessageTypeEnum.GENERATED_CLIENT_UUID, message=self.uuid
        )

        self.socket.send(uuid_message.dump())

        self.client_list.add_client(self)
        self.client_list.update_clients()

        while True:
            try:
                data = self.socket.recv(2065)
                message = self.parse_message(data)
                if message.message_type == MessageTypeEnum.DISCONNECT_NOTIFICATION:
                    logger.info(
                        f"Ending connection with client {client_ip} due to disconnect notification."
                    )
                    break
                self.handle_message(message)
            except Exception as err:
                logger.error(err)
                logger.info("Removing client due to network error")
                break

        self.client_list.remove_client(self)
        self.client_list.update_clients()
        logger.info(f"Client successfully disconnected from {client_ip}")
        del self

    def parse_message(self, data: bytes) -> Message:
        """parse binary data to a Message instance.

        Args:
            data (bytes)

        Returns:
            Message
        """
        try:
            return Message.decode(data)
        except ValueError as err:
            logger.error(err, exc_info=True)
            logger.info("Malformed message received.")
            raise err

    def handle_message(self, message: Message) -> None:
        """Handle a client message. In this instance, there won't be any Disconnection notification message type

        Args:
            message (Message):
        """
        if message.message_type == MessageTypeEnum.CLIENT_TO_SERVER:
            logger.info(f"CLIENT MESSAGE: {message.message}")
            return
        if message.message_type == MessageTypeEnum.UPDATE_CLIENT_ALIAS:
            self.update_alias(message.message)
            logger.info(
                f"Client {self.uuid} updated its alias to {self.alias} successfuly"
            )
            return
        if message.message_type == MessageTypeEnum.CLIENT_TO_CLIENT:
            logger.info(f"Received message from {message.from_}")
            logger.info(message.dump())
            self.send_to_destination(message)
            return

    def send_to_destination(self, message: Message) -> None:
        if not message.destination:
            raise ValueError("Missing destination.")
        logger.info(f"Sending message from {message.from_} to {message.destination}")
        destination_client = self.client_list.get_by_uuid(message.destination)
        destination_client.socket.send(message.dump())

    def update_alias(self, alias: str):
        self.alias = alias
        self.client_list.update_clients()

    def dump(self) -> dict:
        return {"uuid": self.uuid, "alias": self.alias, "address": self.address}


class ClientList:
    def __init__(self):
        """
        Initialize a list to keep track of connected clients.
        """
        self.clients: Set[Client] = set()

    def get_by_uuid(self, uuid: str) -> Client:
        for client in self.clients:
            if client.uuid == uuid:
                return client
        raise ValueError("No client match the given uuid")

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
        if not self.clients:
            logger.info("No clients to send updated list")
            return
        client_list = [client.dump() for client in self.clients]
        message = Message(
            type=MessageTypeEnum.CLIENT_LIST_UPDATE, message=json.dumps(client_list)
        )

        for client in self.clients:
            try:
                client.socket.send(message.dump())
            except Exception as err:
                logger.error(err)
                raise err
        logger.info("Updated client list sent to all connected clients")


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
