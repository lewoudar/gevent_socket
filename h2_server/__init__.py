import json
from typing import Tuple

from gevent import socket, ssl
from gevent.server import StreamServer
from h2 import events
from h2.config import H2Configuration
from h2.connection import H2Connection


# noinspection PyUnresolvedReferences
def get_http2_tls_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
    # RFC 7540 Section 9.2: Implementations of HTTP/2 MUST use TLS version 1.2
    # or higher. Disable TLS 1.1 and lower.
    ctx.options |= (
            ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3 | ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1
    )
    # RFC 7540 Section 9.2.1: A deployment of HTTP/2 over TLS 1.2 MUST disable
    # compression.
    ctx.options |= ssl.OP_NO_COMPRESSION
    ctx.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20')
    ctx.load_cert_chain(certfile='localhost.crt', keyfile='localhost.key')
    ctx.set_alpn_protocols(['h2'])
    try:
        ctx.set_npn_protocols(['h2'])
    except NotImplementedError:
        pass

    return ctx


class H2Worker:

    def __init__(self, sock: socket, address: Tuple[str, str]):
        self._sock = sock
        self._address = address
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


server = StreamServer(('127.0.0.1', 8080), H2Worker, ssl_context=get_http2_tls_context(), server_side=True)
server.serve_forever()
