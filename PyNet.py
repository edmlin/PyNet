from threading import *
import socket
import time


class Server:
    def __init__(self, ip, port):
        self._running = False
        self._socket = None
        self._connections = []
        self.listen_thread = None
        self._max_connections = 2
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind((ip, port))

    def start(self):
        self.listen_thread = Thread(target=self.listen)
        self.listen_thread.start()

    def on_client_connected(self, conn):
        print("Connected from {}:{}. Active connections: {}".format(conn.ip,conn.port,len(self._connections)))
        if len(self._connections) == self._max_connections:
            print("Max connection number reached.")

    def on_client_disconnected(self,conn):
        print("{}:{} disconnected. Active connections:{}".format(conn.ip,conn.port,len(self._connections)))

    def listen(self):
        print("Listening...")
        self._running = True
        while self._running:
            if len(self._connections) < self._max_connections:
                try:
                    self._socket.settimeout(0.2)  # timeout for listening
                    self._socket.listen(1)
                    (conn, (ip, port)) = self._socket.accept()
                except socket.timeout:
                    pass
                else:
                    self.client_connected(conn, ip, port)

    def stop(self):
        self._running = False
        for c in self._connections:
            c.disconnect()
        self.listen_thread.join()
        print("server stopped.")

    def client_connected(self, conn, ip, port):
        connection = Connection(conn, ip, port)
        self._connections.append(connection)
        connection.on_receive = self.on_receive
        connection.on_disconnected=self.client_disconnected
        connection.start_receiving()
        if callable(self.on_client_connected):
            self.on_client_connected(connection)

    def client_disconnected(self,conn):
        self._connections.remove(conn)
        if callable(self.on_client_disconnected):
            self.on_client_disconnected(conn)

    def send(self, msg):
        for conn in self._connections:
            conn.send(msg)

    def on_receive(self, connection, msg):
        msg = "From {}:{}: {}\r\n".format(connection.ip, connection.port, msg)
        print(msg)
        for conn in self._connections:
            if conn is not connection:
                conn.send(msg)


class Client:
    def __init__(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connected = False
        self._trying_to_connect = False
        self.connection = None
        self.on_receive=None
        self.on_connected=None
        self.on_disconnected=None

    def _connect(self, ip, port):
        self._trying_to_connect = True
        print("connecting to {}:{}".format(ip, port))
        while self._trying_to_connect:
            try:
                self._socket.connect((ip, port))
            except:
                pass
            else:
                print("connected")
                self.connected = True
                self._trying_to_connect = False
                self.connection = Connection(self._socket, ip, port)
                self.connection.on_receive = self.on_receive
                self.connection.on_disconnected=self.on_disconnected
                self.connection.start_receiving()
                if callable(self.on_connected):
                    self.on_connected(ip, port)

    def connect(self, ip, port):
        Thread(target=self._connect, args=(ip, port)).start()

    def send(self, msg):
        if self.connected:
            self.connection.send(msg)

    def close(self):
        if self.connection:
            self.connection.disconnect()
        self.connected = False
        self._trying_to_connect = False


class Connection:
    def __init__(self, sck, ip, port):
        self._socket = sck
        self.ip = ip
        self.port = port
        self._message = ""
        self.connected = True
        self.receive_thread = None
        self.on_receive = None
        self.on_disconnected=None
        self.message_separator = "\r\n"

    def start_receiving(self):
        self.receive_thread = Thread(target=self.receive)
        self.receive_thread.start()

    def receive(self):
        self._socket.settimeout(0.2)
        while self.connected:
            try:
                data = self._socket.recv(2048).decode()
                if data is None or len(data) == 0:
                    self.connected = False
                else:
                    if self.message_separator in data:
                        idx = data.index(self.message_separator)
                        if callable(self.on_receive):
                            self.on_receive(self, self._message + data[0:idx])
                        self._message = data[idx + len(self.message_separator):]
                    else:
                        self._message += data
            except socket.timeout:
                pass

        self._socket.close()
        if callable(self.on_disconnected):
            self.on_disconnected(self)

    def send(self, msg):
        Thread(target=self._socket.sendall, args=(msg.encode(),)).start()

    def disconnect(self):
        self.connected = False



if __name__ == '__main__':
    client = Client()
    client.connect("127.0.0.1", 10000)
    client.on_receive=lambda conn,msg:print(msg)
    time.sleep(5)
    server = Server("0.0.0.0", 10000)
    server.start()
    while True:
        command = input("command:")
        if command == 'end':
            client.close()
            server.stop()
            break
        else:
            server.send("From Server: " + command + "\r\n")
