# This file is part of the Trezor project.
#
# Copyright (C) 2012-2022 SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

from __future__ import annotations

import logging
import struct
import typing as t

import requests

from ..client import ProtocolVersion
from ..log import DUMP_PACKETS
from . import DeviceIsBusy, MessagePayload, Transport, TransportException

if t.TYPE_CHECKING:
    from ..models import TrezorModel

LOG = logging.getLogger(__name__)

TREZORD_HOST = "http://127.0.0.1:21325"
TREZORD_ORIGIN_HEADER = {"Origin": "https://python.trezor.io"}

TREZORD_VERSION_MODERN = (2, 0, 25)

CONNECTION = requests.Session()
CONNECTION.headers.update(TREZORD_ORIGIN_HEADER)


class BridgeException(TransportException):
    def __init__(self, path: str, status: int, message: str) -> None:
        self.path = path
        self.status = status
        self.message = message
        super().__init__(f"trezord: {path} failed with code {status}: {message}")


def call_bridge(path: str, data: str | None = None) -> requests.Response:
    url = TREZORD_HOST + "/" + path
    r = CONNECTION.post(url, data=data)
    if r.status_code != 200:
        raise BridgeException(path, r.status_code, r.json()["error"])
    return r


def get_bridge_version() -> t.Tuple[int, ...]:
    config = call_bridge("configure").json()
    return tuple(map(int, config["version"].split(".")))


def is_legacy_bridge() -> bool:
    return get_bridge_version() < TREZORD_VERSION_MODERN


def detect_protocol_version(transport: "BridgeTransport") -> int:
    from .. import mapping, messages

    protocol_version = ProtocolVersion.PROTOCOL_V1
    request_type, request_data = mapping.DEFAULT_MAPPING.encode(messages.Initialize())
    transport.deprecated_begin_session()
    transport.deprecated_write(request_type, request_data)

    response_type, response_data = transport.deprecated_read()
    _ = mapping.DEFAULT_MAPPING.decode(response_type, response_data)
    transport.deprecated_begin_session()

    return protocol_version


def _is_transport_valid(transport: "BridgeTransport") -> bool:
    is_valid = detect_protocol_version(transport) == ProtocolVersion.PROTOCOL_V1
    if not is_valid:
        LOG.warning("Detected unsupported Bridge transport!")
    return is_valid


def filter_invalid_bridge_transports(
    transports: t.Iterable["BridgeTransport"],
) -> t.Sequence["BridgeTransport"]:
    """Filters out invalid bridge transports. Keeps only valid ones."""
    return [t for t in transports if _is_transport_valid(t)]


class BridgeHandle:
    def __init__(self, transport: "BridgeTransport") -> None:
        self.transport = transport

    def read_buf(self) -> bytes:
        raise NotImplementedError

    def write_buf(self, buf: bytes) -> None:
        raise NotImplementedError


class BridgeHandleModern(BridgeHandle):
    def write_buf(self, buf: bytes) -> None:
        LOG.log(DUMP_PACKETS, f"sending message: {buf.hex()}")
        self.transport._call("post", data=buf.hex())

    def read_buf(self) -> bytes:
        data = self.transport._call("read")
        LOG.log(DUMP_PACKETS, f"received message: {data.text}")
        return bytes.fromhex(data.text)


class BridgeHandleLegacy(BridgeHandle):
    def __init__(self, transport: "BridgeTransport") -> None:
        super().__init__(transport)
        self.request: str | None = None

    def write_buf(self, buf: bytes) -> None:
        if self.request is not None:
            raise TransportException("Can't write twice on legacy Bridge")
        self.request = buf.hex()

    def read_buf(self) -> bytes:
        if self.request is None:
            raise TransportException("Can't read without write on legacy Bridge")
        try:
            LOG.log(DUMP_PACKETS, f"calling with message: {self.request}")
            data = self.transport._call("call", data=self.request)
            LOG.log(DUMP_PACKETS, f"received response: {data.text}")
            return bytes.fromhex(data.text)
        finally:
            self.request = None


class BridgeTransport(Transport):
    """
    BridgeTransport implements transport through Trezor Bridge (aka trezord).
    """

    PATH_PREFIX = "bridge"
    ENABLED: bool = True

    def __init__(
        self, device: t.Dict[str, t.Any], legacy: bool, debug: bool = False
    ) -> None:
        if legacy and debug:
            raise TransportException("Debugging not supported on legacy Bridge")
        self.device = device
        self.session: str | None = device["session"]
        self.debug = debug
        self.legacy = legacy

        if legacy:
            self.handle: BridgeHandle = BridgeHandleLegacy(self)
        else:
            self.handle = BridgeHandleModern(self)

    def get_path(self) -> str:
        return f"{self.PATH_PREFIX}:{self.device['path']}"

    def find_debug(self) -> "BridgeTransport":
        if not self.device.get("debug"):
            raise TransportException("Debug device not available")
        return BridgeTransport(self.device, self.legacy, debug=True)

    def _call(self, action: str, data: str | None = None) -> requests.Response:
        session = self.session or "null"
        uri = action + "/" + str(session)
        if self.debug:
            uri = "debug/" + uri
        return call_bridge(uri, data=data)

    @classmethod
    def enumerate(
        cls, _models: t.Iterable["TrezorModel"] | None = None
    ) -> t.Iterable["BridgeTransport"]:
        try:
            legacy = is_legacy_bridge()
            return filter_invalid_bridge_transports(
                [
                    BridgeTransport(dev, legacy)
                    for dev in call_bridge("enumerate").json()
                ]
            )
        except Exception:
            return []

    def deprecated_begin_session(self) -> None:
        try:
            data = self._call("acquire/" + self.device["path"])
        except BridgeException as e:
            if e.message == "wrong previous session":
                raise DeviceIsBusy(self.device["path"]) from e
            raise
        self.session = data.json()["session"]

    def deprecated_end_session(self) -> None:
        if not self.session:
            return
        self._call("release")
        self.session = None

    def deprecated_write(self, message_type: int, message_data: bytes) -> None:
        header = struct.pack(">HL", message_type, len(message_data))
        self.handle.write_buf(header + message_data)

    def deprecated_read(self) -> MessagePayload:
        data = self.handle.read_buf()
        headerlen = struct.calcsize(">HL")
        msg_type, datalen = struct.unpack(">HL", data[:headerlen])
        return msg_type, data[headerlen : headerlen + datalen]

    def open(self) -> None:
        pass
        # TODO self.handle.open()

    def close(self) -> None:
        pass
        # TODO self.handle.close()

    def write_chunk(self, chunk: bytes) -> None:  # TODO check if it works :)
        self.handle.write_buf(chunk)

    def read_chunk(self) -> bytes:  # TODO check if it works :)
        return self.handle.read_buf()
