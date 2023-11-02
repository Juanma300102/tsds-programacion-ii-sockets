from server.server import Server

if __name__ == "__main__":
    HOST = "0.0.0.0"  # localhost
    PORT = 12345  # You can choose any available port

    server = Server(HOST, PORT)
    server.start()
