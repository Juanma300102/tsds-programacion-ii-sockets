import tkinter as tk
from client.client import ClientApp, ClientConnection

if __name__ == "__main__":
    root = tk.Tk()
    connection = ClientConnection()
    app = ClientApp(root, connection)
    root.mainloop()
