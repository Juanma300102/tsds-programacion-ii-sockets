import json
from json.decoder import JSONDecodeError
import tkinter as tk
from tkinter import ttk, messagebox
import socket
import threading
import logging
from shared import Message, MessageTypeEnum


# Create a logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Configure the logger
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)


class ClientConnection:
    port: int
    host: str
    client_socket: socket.socket

    def set_host_port(self, host: str, port: int):
        self.host = host
        self.port = port

    def connect(self):
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.host, self.port))
        except ConnectionRefusedError as err:
            messagebox.showerror(title="Connection error", message=err.strerror)

    def receive_message(self) -> Message | None:
        try:
            data = self.client_socket.recv(1024)
            logger.info(data)
            loaded = json.loads(data.decode("utf-8"))
            return Message(
                type=MessageTypeEnum(int(loaded["message_type"])),
                message=loaded["message"],
                destination=loaded["destination"],
            )
        except JSONDecodeError as err:
            raise err
        except ValueError as err:
            logger.error(err, exc_info=True)
            logger.info("Malformed message received. Skipping...")
            return None
        except Exception as err:
            raise err

    def send_message(self, message: bytes):
        self.client_socket.send(message)


class ClientApp:
    def __init__(self, root: tk.Tk, connection: ClientConnection):
        self.root = root
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
        """ self.client_listbox = tk.Listbox(
            root, selectmode=tk.SINGLE, listvariable=self.client_list
            self.client_listbox.pack()
        ) """
        self.client_listselect.pack()

        self.message_display_label = tk.Label(root, text="Server Messages:")
        self.message_display_label.pack()
        self.message_display = tk.Text(root, height=10, width=40)
        self.message_display.pack()

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

    def disconnect_from_server(self):
        if self.connected:
            # Close the connection and reset UI elements
            self.connection.client_socket.close()

            self.connected = False
            self.connect_button.config(state=tk.NORMAL)
            self.host_entry.config(state=tk.NORMAL)
            self.port_entry.config(state=tk.NORMAL)
            self.text_input_entry.config(state=tk.DISABLED)
            self.send_button.config(state=tk.DISABLED)
            self.disconnect_button.config(state=tk.DISABLED)

    def connect_to_server(self):
        host = self.host_entry.get()
        port = int(self.port_entry.get())
        self.connected = True
        self.connection.set_host_port(host, port)
        self.connection.connect()

        # Enable/disable GUI elements based on the connection state
        self.connect_button.config(state=tk.DISABLED)
        self.host_entry.config(state=tk.DISABLED)
        self.port_entry.config(state=tk.DISABLED)
        self.text_input_entry.config(state=tk.NORMAL)
        self.send_button.config(state=tk.NORMAL)

        # Start a thread to receive messages
        self.receive_thread = threading.Thread(target=self.receive_messages)
        self.receive_thread.start()

    def receive_messages(self):
        while self.connected:
            try:
                message = self.connection.receive_message()
                if message:
                    self.handle_message(message)
                """ 
                else:
                    # Handle disconnection """
            except JSONDecodeError:
                self.disconnect_from_server()
                self.display_message("Server connection closed.")

    def send_message(self):
        message = Message(
            message=self.text_input_entry.get(), type=MessageTypeEnum.CLIENT_TO_SERVER
        )
        self.connection.send_message(message.dump())
        self.display_message(f"You: {message.message}")
        self.text_input_entry.delete(0, tk.END)

    def handle_message(self, message: Message):
        if message.message_type == MessageTypeEnum.CLIENT_LIST_UPDATE:
            self.client_listselect["values"] = message.message.split(",")
            return
        self.display_message(message.message)

    def display_message(self, message: str):
        self.message_display.insert(tk.END, message + "\n")
        self.message_display.see(tk.END)
