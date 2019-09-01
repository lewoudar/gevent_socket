"""
Simple websocket client
"""
import re
from typing import Callable, Tuple, List, Dict

from gevent import socket
from wsproto import WSConnection, ConnectionType
from wsproto.events import Request, AcceptConnection, CloseConnection
from wsproto.typing import Headers


class Client:
    _callbacks: Dict[str, Callable] = {}
    receive_bytes = 65535

    # noinspection PyTypeChecker
    def __init__(self, connect_uri: str, headers: Headers = None, extensions: List[str] = None,
                 sub_protocols: List[str] = None):
        self._check_ws_headers(headers)
        self._check_list_argument('extensions', extensions)
        self._check_list_argument('sub_protocols', sub_protocols)

        self._sock: socket = None
        self._ws: WSConnection = None
        # wsproto does not seem to like empty path, so we provide an arbitrary one
        self._default_path = 'path'

        host, port, path = self._get_connect_information(connect_uri)
        self._establish_tcp_connection(host, port)
        self._establish_websocket_handshake(host, path, headers, extensions, sub_protocols)

    @staticmethod
    def _check_ws_headers(headers: Headers) -> None:
        if headers is None:
            return

        error_message = 'headers must of a list of tuples of the form [(bytes, bytes), ..]'
        if not isinstance(headers, list):
            raise TypeError(error_message)

        try:
            for key, value in headers:
                if not isinstance(key, bytes) or not isinstance(value, bytes):
                    raise TypeError(error_message)
        except ValueError:  # in case it is not a list of tuples
            raise TypeError(error_message)

    @staticmethod
    def _check_list_argument(name: str, ws_argument: List[str]) -> None:
        if ws_argument is None:
            return

        error_message = f'{name} must be a list of strings'
        if not isinstance(ws_argument, list):
            raise TypeError(error_message)
        for item in ws_argument:
            if not isinstance(item, str):
                raise TypeError(error_message)

    def _get_connect_information(self, connect_uri: str) -> Tuple[str, int, str]:
        if not isinstance(connect_uri, str):
            raise TypeError('Your uri must be a string')

        regex = re.match(r'ws://(\w+)(:\d+)?(/\w+)?', connect_uri)
        if not regex:
            raise ValueError('Your uri must follow the syntax ws://<host>[:port][/path]')

        host = regex.group(1)
        port = int(regex.group(2)[1:]) if regex.group(2) is not None else 80
        path = regex.group(3)[1:] if regex.group(3) is not None else self._default_path
        return host, port, path

    @staticmethod
    def _check_callable(method: str, callback: Callable) -> None:
        if not isinstance(callback, callable):
            raise TypeError(f'{method} callback must be a callable')

    def _establish_tcp_connection(self, host: str, port: int) -> None:
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.connect((host, port))

    def _establish_websocket_handshake(self, host: str, path: str, headers: Headers, extensions: List[str],
                                       sub_protocols: List[str]) -> None:
        self._ws = WSConnection(ConnectionType.CLIENT)
        headers = headers if headers is not None else []
        extensions = extensions if extensions is not None else []
        sub_protocols = sub_protocols if sub_protocols is not None else []
        request = Request(host=host, target=path, extra_headers=headers, extensions=extensions,
                          subprotocols=sub_protocols)
        self._sock.sendall(self._ws.send(request))
        in_data = self._sock.recv(self.receive_bytes)
        self._ws.receive_data(in_data)
        self._handle_events()

    def _handle_events(self):
        for event in self._ws.events():
            if isinstance(event, AcceptConnection):
                print('connection established')
            if isinstance(event, CloseConnection):
                print('connection terminated')

    def _close_ws_connection(self):
        close_data = self._ws.send(CloseConnection(code=1000, reason='nothing more to do'))
        self._sock.sendall(close_data)

        self._ws.receive_data(self._sock.recv(self.receive_bytes))
        self._handle_events()
        self._sock.shutdown(socket.SHUT_WR)

        in_data = self._sock.recv(self.receive_bytes)
        if not in_data:
            self._ws.receive_data(None)
        else:
            self._ws.receive_data(in_data)

    def _close_socket(self) -> None:
        self._sock.close()

    def close(self) -> None:
        self._close_ws_connection()
        self._close_socket()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return True


if __name__ == '__main__':
    # client = Client('ws://localhost:8080/foo')
    # client.close()
    with Client('ws://localhost:8080/foo'):
        pass
