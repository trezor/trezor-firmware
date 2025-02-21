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
from typing import TYPE_CHECKING, Any, Iterable

import requests
from typing_extensions import Self

from ..log import DUMP_PACKETS
from . import DeviceIsBusy, MessagePayload, Transport, TransportException

if TYPE_CHECKING:
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


def call_bridge(
    path: str, data: str | None = None, timeout: float | None = None
) -> requests.Response:
    url = TREZORD_HOST + "/" + path
    r = CONNECTION.post(url, data=data, timeout=timeout)
    if r.status_code != 200:
        raise BridgeException(path, r.status_code, r.json()["error"])
    return r


def is_legacy_bridge() -> bool:
    config = call_bridge("configure").json()
    version_tuple = tuple(map(int, config["version"].split(".")))
    return version_tuple < TREZORD_VERSION_MODERN


class BridgeHandle:
    def __init__(self, transport: "BridgeTransport") -> None:
        self.transport = transport

    def read_buf(self, timeout: float | None = None) -> bytes:
        raise NotImplementedError

    def write_buf(self, buf: bytes) -> None:
        raise NotImplementedError


class BridgeHandleModern(BridgeHandle):
    def write_buf(self, buf: bytes) -> None:
        LOG.log(DUMP_PACKETS, f"sending message: {buf.hex()}")
        self.transport._call("post", data=buf.hex())

    def read_buf(self, timeout: float | None = None) -> bytes:
        data = self.transport._call("read", timeout=timeout)
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

    def read_buf(self, timeout: float | None = None) -> bytes:
        if self.request is None:
            raise TransportException("Can't read without write on legacy Bridge")
        try:
            LOG.log(DUMP_PACKETS, f"calling with message: {self.request}")
            data = self.transport._call("call", data=self.request, timeout=timeout)
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
        self, device: dict[str, Any], legacy: bool, debug: bool = False
    ) -> None:
        if legacy and debug:
            raise TransportException("Debugging not supported on legacy Bridge")

        self.device = device
        self.session: str | None = None
        self.debug = debug
        self.legacy = legacy

        if legacy:
            self.handle: BridgeHandle = BridgeHandleLegacy(self)
        else:
            self.handle = BridgeHandleModern(self)

    def get_path(self) -> str:
        return f"{self.PATH_PREFIX}:{self.device['path']}"

    def find_debug(self) -> Self:
        if not self.device.get("debug"):
            raise TransportException("Debug device not available")
        return self.__class__(self.device, self.legacy, debug=True)

    def _call(
        self,
        action: str,
        data: str | None = None,
        timeout: float | None = None,
    ) -> requests.Response:
        session = self.session or "null"
        uri = action + "/" + str(session)
        if self.debug:
            uri = "debug/" + uri
        return call_bridge(uri, data=data, timeout=timeout)

    @classmethod
    def enumerate(
        cls, _models: Iterable[TrezorModel] | None = None
    ) -> Iterable["BridgeTransport"]:
        try:
            legacy = is_legacy_bridge()
            return [
                BridgeTransport(dev, legacy) for dev in call_bridge("enumerate").json()
            ]
        except Exception:
            return []

    def begin_session(self) -> None:
        try:
            data = self._call("acquire/" + self.device["path"])
        except BridgeException as e:
            if e.message == "wrong previous session":
                raise DeviceIsBusy(self.device["path"]) from e
            raise
        self.session = data.json()["session"]

    def end_session(self) -> None:
        if not self.session:
            return
        self._call("release")
        self.session = None

    def write(self, message_type: int, message_data: bytes) -> None:
        header = struct.pack(">HL", message_type, len(message_data))
        self.handle.write_buf(header + message_data)

    def read(self, timeout: float | None = None) -> MessagePayload:
        data = self.handle.read_buf(timeout=timeout)
        headerlen = struct.calcsize(">HL")
        msg_type, datalen = struct.unpack(">HL", data[:headerlen])
        return msg_type, data[headerlen : headerlen + datalen]
