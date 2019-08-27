import json
from typing import Tuple

from gevent import socket
from gevent.server import StreamServer
from h2 import events
from h2.config import H2Configuration
from h2.connection import H2Connection


class H2Worker:

    def __init__(self, sock: socket, address: Tuple[str, str]):
        self._sock: socket = sock
        # noinspection PyTypeChecker
        self._address: Tuple[str, str] = address
        self._run()

    @staticmethod
    def _prepare_response(connection: H2Connection, event: events.RequestReceived) -> None:
        stream_id = event.stream_id
        str_headers = {key.decode(): value.decode() for key, value in event.headers}
        response_data = json.dumps(dict(str_headers)).encode()

        connection.send_headers(
            stream_id=stream_id,
            headers=[
                (':status', '200'),
                ('server', 'basic-h2_server-server/1.0'),
                ('content-length', str(len(response_data))),
                ('content-type', 'application/json'),
            ],
        )
        connection.send_data(
            stream_id=stream_id,
            data=response_data,
            end_stream=True
        )

    def _close(self) -> None:
        self._sock.shutdown(socket.SHUT_WR)
        self._sock.close()

    def _run(self) -> None:
        conn = H2Connection(H2Configuration(client_side=False))
        conn.initiate_connection()
        self._sock.sendall(conn.data_to_send())

        while True:
            data = self._sock.recv(65535)
            if not data:
                break
            h2_events = conn.receive_data(data)
            for event in h2_events:
                if isinstance(event, events.RequestReceived):
                    self._prepare_response(conn, event)

            data_to_send = conn.data_to_send()
            if data_to_send:
                self._sock.sendall(data_to_send)

        self._close()


server = StreamServer(('127.0.0.1', 8080), H2Worker)
server.serve_forever()
