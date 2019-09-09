# gevent socket

Just playing with gevent, socket, h2 and wsproto.
May be later I will finalize it in a package..

The project contains:
- a HTTP/2 server serving static files
- a websocket client

It you want to test it, follow the instructions below.

## dependencies

To install the dependencies, you just need to run the following command:

`pipenv install`

If you don't know pipenv and how to install, look at the documentation [here](https://docs.pipenv.org/en/latest/).
It is a great tool for developing!

## HTTP/2

To use the http/2 server, enter the `h2_server` the following command:

python __init__.py <optional path>

the server will listen on port 8080 and will serve files from the path you provided as input or the current working
directory if you haven't provided one

## websocket client

Code sample

```python
from websockets.client import Client
from wsproto.events import AcceptConnection, CloseConnection

@Client.on_connect
def connect(client: Client, event: AcceptConnection):
    print('connection accepted')
    print(event)


@Client.on_disconnect
def disconnect(client: Client, event: CloseConnection):
    print('connection closed')
    print(event)


@Client.on_pong
def pong(payload):
    print('pong message:', payload)


@Client.on_json_message
def handle_json_message(payload):
    print('json message:', payload)

@Client.on_text_message
def handle_text_message(payload):
    print('text message:', payload)


@Client.on_binary_message
def handle_binary_message(payload):
    print('binary message:', payload)


with Client('ws://localhost:8080/foo') as client:
    client.ping()
    client.send_json({'hello': 'world'})
    client.send('my name is Kevin')
    client.send(b'just some bytes for testing purpose')
```

Notes:
- If the server sends json data you will receive it on json handler and not text handler
- I don't know why but ws_proto demands a path when giving the string connection so if you use a string connection like
this one `ws://localhost:8080` the client adds a default path called `path`.
- SSL is not supported.