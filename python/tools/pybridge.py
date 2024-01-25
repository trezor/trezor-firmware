#!/usr/bin/env python3
# ### INSTRUCTIONS FOR USE ####
#
# 1. install Python 3.7 and up
# 2. make sure you have `pip3` command available
# 3. from command line, run the following:
#        pip3 install trezor[hidapi] gevent bottle
# 4. (ONLY for TT or T1 >= 1.8.0) Make sure you have libusb available.
#    4a. on Windows, download:
#        https://github.com/libusb/libusb/releases/download/v1.0.26/libusb-1.0.26-binaries.7z
#        Extract file VS2015-x64/dll/libusb-1.0.dll and place it in your working directory.
#    4b. on MacOS, assuming you have Homebrew, run `brew install libusb`
#        Otherwise download the above, extract the file macos_<best version>/lib/libusb.1.0.0.dylib
#        and place it in your working directory.
#    4c. on Linux, use your package manager to install `libusb` or `libusb-1.0` package.
#        (but on Linux you most likely already have it)
# 4. Shut down Trezor Suite (and bridge if you are running it separately
# 5. Disconnect and then reconnect your Trezor.
# 6. Run the following command from the command line:
#        python3 pybridge.py
# 7. Start Suite again, or use any other Trezor-compatible software.
# 8. Output of pybridge goes to console and also to file `pybridge.log`
from __future__ import annotations

from gevent import monkey

monkey.patch_all()

import json
import logging
import struct
import time
import typing as t

import click
from bottle import post, request, response, run

import trezorlib.mapping
import trezorlib.models
import trezorlib.transport
from trezorlib.client import TrezorClient
from trezorlib.protobuf import format_message
from trezorlib.transport.bridge import BridgeTransport
from trezorlib.ui import TrezorClientUI

# ignore bridge. we are the bridge
BridgeTransport.ENABLED = False


logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler("pybridge.log"),
        logging.StreamHandler(),
    ],
)

LOG = logging.getLogger()


class SilentUI(TrezorClientUI):
    def get_pin(self, _code: t.Any) -> str:
        return ""

    def get_passphrase(self) -> str:
        return ""

    def button_request(self, _br: t.Any) -> None:
        pass


class Session:
    SESSION_COUNTER = 0
    SESSIONS: dict[str, Session] = {}

    def __init__(self, transport: Transport) -> None:
        self.id = self._new_id()
        self.transport = transport
        self.SESSIONS[self.id] = self

    def release(self) -> None:
        self.SESSIONS.pop(self.id, None)
        self.transport.release()

    @classmethod
    def find(cls, sid: str) -> Session | None:
        return cls.SESSIONS.get(sid)

    @classmethod
    def _new_id(cls) -> str:
        id = str(cls.SESSION_COUNTER)
        cls.SESSION_COUNTER += 1
        return id


class Transport:
    TRANSPORT_COUNTER = 0
    TRANSPORTS: dict[str, Transport] = {}

    def __init__(self, transport: trezorlib.transport.Transport) -> None:
        self.path = transport.get_path()
        self.session: Session | None = None
        self.transport = transport

        client = TrezorClient(transport, ui=SilentUI())
        self.model = (
            trezorlib.models.by_name(client.features.model) or trezorlib.models.TREZOR_T
        )
        client.end_session()

    def acquire(self, sid: str) -> str:
        if self.session_id() != sid:
            raise Exception("Session mismatch")
        if self.session is not None:
            self.session.release()

        self.session = Session(self)
        self.transport.begin_session()
        return self.session.id

    def release(self) -> None:
        self.transport.end_session()
        self.session = None

    def session_id(self) -> str | None:
        if self.session is not None:
            return self.session.id
        else:
            return None

    def to_json(self) -> dict:
        vid, pid = next(iter(self.model.usb_ids), (0, 0))
        return {
            "debug": False,
            "debugSession": None,
            "path": self.path,
            "product": pid,
            "vendor": vid,
            "session": self.session_id(),
        }

    def write(self, msg_id: int, data: bytes) -> None:
        self.transport.write(msg_id, data)

    def read(self) -> tuple[int, bytes]:
        return self.transport.read()

    @classmethod
    def find(cls, path: str) -> Transport | None:
        return cls.TRANSPORTS.get(path)

    @classmethod
    def enumerate(cls) -> t.Iterable[Transport]:
        transports = {t.get_path(): t for t in trezorlib.transport.enumerate_devices()}
        for path in transports:
            if path not in cls.TRANSPORTS:
                cls.TRANSPORTS[path] = Transport(transports[path])

        for path in list(cls.TRANSPORTS):
            if path not in transports:
                cls.TRANSPORTS.pop(path, None)

        return cls.TRANSPORTS.values()


FILTERS: dict[int, t.Callable[[int, bytes], tuple[int, bytes]]] = {}


def log_message(prefix: str, msg_id: int, data: bytes) -> None:
    try:
        msg = trezorlib.mapping.DEFAULT_MAPPING.decode(msg_id, data)
        LOG.info("=== %s: [%s] %s", prefix, msg_id, format_message(msg))
    except Exception:
        LOG.info("=== %s: [%s] undecoded bytes %s", prefix, msg_id, data.hex())


def decode_data(hex_data: str) -> tuple[int, bytes]:
    data = bytes.fromhex(hex_data)
    headerlen = struct.calcsize(">HL")
    msg_type, datalen = struct.unpack(">HL", data[:headerlen])
    return msg_type, data[headerlen : headerlen + datalen]


def encode_data(msg_type: int, msg_data: bytes) -> str:
    data = struct.pack(">HL", msg_type, len(msg_data)) + msg_data
    return data.hex()


def check_origin() -> None:
    response.set_header("Access-Control-Allow-Origin", "*")


@post("/")  # type: ignore [Untyped function decorator]
def index():
    check_origin()
    return {"version": "2.0.27"}


@post("/configure")  # type: ignore [Untyped function decorator]
def do_configure():
    return index()


@post("/enumerate")  # type: ignore [Untyped function decorator]
def do_enumerate():
    check_origin()
    trezor_json = [transport.to_json() for transport in Transport.enumerate()]
    return json.dumps(trezor_json)


@post("/acquire/<path>/<sid>")  # type: ignore [Untyped function decorator]
def do_acquire(path: str, sid: str):
    check_origin()
    if sid == "null":
        sid = None  # type: ignore [cannot be assigned to declared type]
    trezor = Transport.find(path)
    if trezor is None:
        response.status = 404
        return {"error": "invalid path"}

    try:
        return {"session": trezor.acquire(sid)}
    except Exception:
        response.status = 400
        return {"error": "wrong previous session"}


@post("/release/<sid>")  # type: ignore [Untyped function decorator]
def do_release(sid: str):
    check_origin()
    session = Session.find(sid)
    if session is None:
        response.status = 404
        return {"error": "invalid session"}
    session.release()
    return {"session": sid}


@post("/call/<sid>")  # type: ignore [Untyped function decorator]
def do_call(sid: str):
    check_origin()
    session = Session.find(sid)
    if session is None:
        response.status = 404
        return {"error": "invalid session"}

    msg_type, msg_data = decode_data(request.body.read().decode())

    if msg_type in FILTERS:
        msg_type, msg_data = FILTERS[msg_type](msg_type, msg_data)
    log_message("CALLING", msg_type, msg_data)

    session.transport.write(msg_type, msg_data)
    resp_type, resp_data = session.transport.read()

    if resp_type in FILTERS:
        resp_type, resp_data = FILTERS[resp_type](resp_type, resp_data)
    log_message("RESPONSE", resp_type, resp_data)

    return encode_data(resp_type, resp_data)


@post("/post/<sid>")  # type: ignore [Untyped function decorator]
def do_post(sid: str):
    check_origin()
    session = Session.find(sid)
    if session is None:
        response.status = 404
        return {"error": "invalid session"}

    msg_type, msg_data = decode_data(request.body.read().decode())
    session.transport.write(msg_type, msg_data)
    return {"session": sid}


@post("/read/<sid>")  # type: ignore [Untyped function decorator]
def do_read(sid: str):
    check_origin()
    session = Session.find(sid)
    if session is None:
        response.status = 404
        return {"error": "invalid session"}

    resp_type, resp_data = session.transport.read()
    print("=== RESPONSE:")
    msg = trezorlib.mapping.DEFAULT_MAPPING.decode(resp_type, resp_data)
    print(format_message(msg))

    return encode_data(resp_type, resp_data)


@post("/listen")  # type: ignore [Untyped function decorator]
def do_listen():
    check_origin()
    try:
        data = json.load(request.body)
    except Exception:
        response.status = 400
        return {"error": "invalid json"}

    for _ in range(10):
        trezor_json = [transport.to_json() for transport in Transport.enumerate()]
        if trezor_json != data:
            # `yield` turns the function into a generator which allows gevent to
            # run it in a greenlet, so that the time.sleep() call doesn't block
            yield json.dumps(trezor_json)
            return
        time.sleep(1)


# def example_filter(msg_id: int, data: bytes) -> tuple[int, bytes]:
#     msg = trezorlib.mapping.DEFAULT_MAPPING.decode(msg_id, data)
#     assert isinstance(msg, messages.Features)
#     msg.model = "Example"
#     return trezorlib.mapping.DEFAULT_MAPPING.encode(msg)


# FILTERS[messages.Features.MESSAGE_WIRE_TYPE] = example_filter


@click.command()
@click.argument("port", type=int, default=21325)
def main(port: int) -> None:
    run(host="127.0.0.1", port=port, server="gevent")


if __name__ == "__main__":
    main()
