import json
from json.decoder import JSONDecodeError
import tkinter as tk
from tkinter import ttk, messagebox
import socket
import threading
import logging
from shared import Message, MessageTypeEnum
from typing import Dict, List
from sys import stdout

# Create a logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Configure the logger
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
stream_handler = logging.StreamHandler(stdout)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)


class ClientConnection:
    port: int
    host: str
    client_socket: socket.socket
    alias: str
    uuid: str

    def __init__(self) -> None:
        self.alias = ""

    def set_host_port(self, host: str, port: int):
        self.host = host
        self.port = port

    def set_alias(self, alias: str) -> None:
        self.alias = alias

    def set_uuid(self, uuid: str) -> None:
        self.uuid = uuid

    def connect(self):
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.host, self.port))
        except ConnectionRefusedError as err:
            messagebox.showerror(
                title="Connection error",
                message="Couldn't connect. Is the server running?",
            )
            raise err

    def receive_message(self) -> Message | None:
        try:
            data = self.client_socket.recv(1024)
            return Message.decode(data)
        except JSONDecodeError as err:
            raise err
        except ValueError as err:
            logger.error(err, exc_info=True)
            logger.info("Malformed message received. Skipping...")
            return None
        except Exception as err:
            raise err

    def send_message(self, message: bytes):
        try:
            self.client_socket.send(message)
        except Exception as err:
            logger.error(err)
            raise err

    def handle_disconnection(self):
        self.alias = ""
        self.uuid = ""

    def make_message(
        self,
        message: str,
        destination: str | None = None,
        type: MessageTypeEnum = MessageTypeEnum.CLIENT_TO_SERVER,
    ) -> Message:
        """Generates a Message instance.

        Args:
            message (str)
            destination (str | None, optional): Defaults to None.
            type (MessageTypeEnum, optional): Defaults to MessageTypeEnum.CLIENT_TO_SERVER.

        Returns:
            Message: _description_
        """
        instance = Message(message=message, type=type, destination=destination)
        if type == MessageTypeEnum.CLIENT_TO_CLIENT:
            logger.info(f"Injecting uuid into message {self.uuid}")
            instance.from_ = self.uuid
        return instance

    def send_disconnect_notification(self):
        """Notify the server to finish the connection when triggered by user."""
        message = self.make_message(
            message="", type=MessageTypeEnum.DISCONNECT_NOTIFICATION
        )
        self.send_message(message.dump())

    def close(self):
        self.client_socket.close()


class ClientApp:
    raw_client_list: List[Dict[str, str]]

    def __init__(self, root: tk.Tk, connection: ClientConnection):
        self.root = root
        self.root.config(padx=10, pady=10)
        self.root.title("Client")

        self.connection = connection

        self.host_label = tk.Label(root, text="Server Host:")
        self.host_label.pack()
        self.host_entry = tk.Entry(root)
        self.host_entry.pack()

        self.port_label = tk.Label(root, text="Server Port:")
        self.port_label.pack()
        self.port_entry = tk.Entry(root)
        self.port_entry.pack()

        self.alias_frame = tk.LabelFrame(root, text="Nickname")
        self.alias_frame.config(padx=10, pady=10)

        self.alias_label = tk.Label(self.alias_frame, text="Client nickname:")
        self.alias_label.pack()
        self.alias_entry = tk.Entry(self.alias_frame)
        self.alias_entry.pack()
        self.update_nickname_button = tk.Button(
            self.alias_frame,
            text="Update",
            command=self.update_nickname,
            state=tk.DISABLED,
        )
        self.update_nickname_button.pack()

        self.alias_frame.pack()

        self.connect_button = tk.Button(
            root, text="Connect", command=self.connect_to_server
        )
        self.connect_button.pack()

        self.client_list = tk.Variable(root, [])

        self.client_list_label = tk.Label(root, text="Connected Clients:")
        self.client_list_label.pack()
        self.client_listselect = ttk.Combobox(
            root, values=self.client_list.get(), state="readonly"
        )
        self.client_listselect.pack(fill=tk.X)

        self.message_display_label = tk.Label(root, text="Server Messages:")
        self.message_display_label.pack()
        self.message_display = tk.Text(root, height=10, width=40, state=tk.DISABLED)
        self.message_display.pack(fill=tk.X)

        self.text_input_label = tk.Label(root, text="Your Message:")
        self.text_input_label.pack()
        self.text_input_entry = tk.Entry(root)
        self.text_input_entry.pack()

        self.send_button = tk.Button(root, text="Send", command=self.send_message)
        self.send_button.pack()

        # self.connect_button.config(state=tk.DISABLED)
        self.connected = False

        self.disconnect_button = tk.Button(
            root, text="Disconnect", command=self.disconnect_from_server
        )
        self.disconnect_button.pack()

    def handle_disconnection(self):
        """Subsequent events following a disconnection from the server.
        This may be triggered by several events like network error or user intentional disconnection.
        """
        self.connected = False
        self.connect_button.config(state=tk.NORMAL)
        self.host_entry.config(state=tk.NORMAL)
        self.port_entry.config(state=tk.NORMAL)
        self.text_input_entry.config(state=tk.DISABLED)
        self.send_button.config(state=tk.DISABLED)
        self.disconnect_button.config(state=tk.DISABLED)
        self.update_nickname_button.config(state=tk.DISABLED)
        self.client_listselect.set("")
        self.client_listselect["values"] = []
        self.clear_messages()
        self.connection.handle_disconnection()

    def connect_to_server(self):
        """
        UI command to validate inputs and stablish connection with the server.
        Also it sets the ui config for the connected client status.
        """
        host = self.host_entry.get()
        port = int(self.port_entry.get())
        self.connection.set_host_port(host, port)
        self.connection.connect()
        self.connected = True

        # Enable/disable GUI elements based on the connection state
        self.connect_button.config(state=tk.DISABLED)
        self.host_entry.config(state=tk.DISABLED)
        self.port_entry.config(state=tk.DISABLED)
        self.text_input_entry.config(state=tk.NORMAL)
        self.send_button.config(state=tk.NORMAL)
        self.disconnect_button.config(state=tk.NORMAL)
        self.update_nickname_button.config(state=tk.NORMAL)

        # Start a thread to receive messages
        self.receive_thread = threading.Thread(target=self.receive_messages)
        self.receive_thread.start()

        # Look if there is a nickname in the entry and update it
        nick = self.alias_entry.get()
        if nick:
            update_nickname_thread = threading.Thread(target=self.update_nickname)
            update_nickname_thread.start()

        self.display_message(
            f"Connected to server at {self.connection.host}:{self.connection.port}"
        )

    def receive_messages(self):
        """Socket message main handler."""
        while True:
            try:
                message = self.connection.receive_message()
                if message:
                    self.handle_incoming_message(message)
            except JSONDecodeError:
                self.handle_disconnection()
                self.display_message("Server connection closed.")
                break
            except OSError as err:
                self.handle_disconnection()
                break

    def handle_incoming_message(self, message: Message):
        """Handle parsed incoming messages based on message_type.

        Args:
            message (Message)
        """
        if message.message_type == MessageTypeEnum.CLIENT_LIST_UPDATE:
            clients = self.parse_client_list(message.message)
            self.raw_client_list = clients
            clients = [
                client for client in clients if client["uuid"] != self.connection.uuid
            ]
            self.client_listselect["values"] = [
                f"{client['alias']}@{client['uuid']}"
                if client["alias"] != ""
                else f"{client['address'][0]}@{client['uuid']}"
                for client in clients
            ]
            self.client_listselect.set("")
            return
        if message.message_type == MessageTypeEnum.GENERATED_CLIENT_UUID:
            self.connection.set_uuid(message.message)
            logger.info(f"Received system uuid {message.message}")
            return
        if message.message_type == MessageTypeEnum.CLIENT_TO_CLIENT:
            if not message.from_:
                raise ValueError("Missing from property in message.")
            client = self.get_raw_client_by_uuid(message.from_)
            self.display_message(
                f"{client['alias'] if client['alias'] else client['address'][0]} to you: {message.message}"
            )
            return
        self.display_message(message.message)

    def parse_client_list(self, data: str | bytes) -> List[Dict[str, str]]:
        """takes a json formated string and loads it to internal object

        Args:
            data (str | bytes)

        Returns:
            List[Dict[str, str]]
        """
        return json.loads(data)

    def send_message(self):
        """UI command to send a message with the current user input content."""
        destination = self.client_listselect.get()
        if not destination:
            messagebox.showerror(
                title="Missing destination",
                message="You must select a client destination",
            )
            return
        client = destination.split("@")[0]
        uuid = destination.split("@")[1]
        message = self.connection.make_message(
            message=self.text_input_entry.get(),
            type=MessageTypeEnum.CLIENT_TO_CLIENT,
            destination=uuid,
        )
        self.connection.send_message(message.dump())
        self.display_message(f"You to {client}: {message.message}")
        self.text_input_entry.delete(0, tk.END)

    def disconnect_from_server(self):
        """UI command for disconnecting from the server."""
        if self.connected:
            self.connection.send_disconnect_notification()
            # Close the connection and reset UI elements
            self.connection.close()
            self.handle_disconnection()

    def display_message(self, message: str):
        """UI command to add a message to the text display

        Args:
            message (str)
        """
        self.message_display.config(state=tk.NORMAL)
        self.message_display.insert(tk.END, message + "\n")
        self.message_display.see(tk.END)
        self.message_display.config(state=tk.DISABLED)

    def clear_messages(self) -> None:
        """Clear the messages display"""
        self.message_display.config(state=tk.NORMAL)
        self.message_display.delete(1.0, tk.END)
        self.message_display.config(state=tk.DISABLED)

    def update_nickname(self) -> None:
        """Validates and updates the client nickname"""
        nickname = self.alias_entry.get()
        if nickname == "":
            messagebox.showwarning(
                title="Invalid nickname", message="Nickname can't be empty"
            )
            return
        if nickname == self.connection.alias:
            messagebox.showwarning(
                title="Invalid nickname", message="The same nickname is already set."
            )
            return
        message = self.connection.make_message(
            message=nickname, type=MessageTypeEnum.UPDATE_CLIENT_ALIAS
        )
        self.connection.send_message(message.dump())
        self.connection.set_alias(nickname)
        self.display_message("Nickname updated successfully")

    def get_raw_client_by_uuid(self, uuid: str) -> Dict[str, str]:
        for client in self.raw_client_list:
            if client["uuid"] == uuid:
                return client
        raise ValueError("No raw client matches the uuid.")
