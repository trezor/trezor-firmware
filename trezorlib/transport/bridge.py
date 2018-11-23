# This file is part of the Trezor project.
#
# Copyright (C) 2012-2018 SatoshiLabs and contributors
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

import logging
import struct
from io import BytesIO
from typing import Any, Dict, Iterable, Optional

import requests

from . import Transport, TransportException
from .. import mapping, protobuf

if False:
    # mark Optional as used, otherwise it only exists in comments
    Optional

LOG = logging.getLogger(__name__)

TREZORD_HOST = "http://127.0.0.1:21325"
TREZORD_ORIGIN_HEADER = {"Origin": "https://python.trezor.io"}

TREZORD_VERSION_MODERN = (2, 0, 25)

CONNECTION = requests.Session()
CONNECTION.headers.update(TREZORD_ORIGIN_HEADER)


def call_bridge(uri: str, data=None) -> requests.Response:
    url = TREZORD_HOST + "/" + uri
    r = CONNECTION.post(url, data=data)
    if r.status_code != 200:
        error_str = "trezord: {} failed with code {}: {}".format(
            uri, r.status_code, r.json()["error"]
        )
        raise TransportException(error_str)
    return r


def is_legacy_bridge() -> bool:
    config = call_bridge("configure").json()
    version_tuple = tuple(map(int, config["version"].split(".")))
    return version_tuple < TREZORD_VERSION_MODERN


class BridgeHandle:
    def __init__(self, transport: "BridgeTransport") -> None:
        self.transport = transport

    def read_buf(self) -> bytes:
        raise NotImplementedError

    def write_buf(self, buf: bytes) -> None:
        raise NotImplementedError


class BridgeHandleModern(BridgeHandle):
    def write_buf(self, buf: bytes) -> None:
        self.transport._call("post", data=buf.hex())

    def read_buf(self) -> bytes:
        data = self.transport._call("read")
        return bytes.fromhex(data.text)


class BridgeHandleLegacy(BridgeHandle):
    def __init__(self, transport: "BridgeTransport") -> None:
        super().__init__(transport)
        self.request = None  # type: Optional[str]

    def write_buf(self, buf: bytes) -> None:
        if self.request is not None:
            raise TransportException("Can't write twice on legacy Bridge")
        self.request = buf.hex()

    def read_buf(self) -> bytes:
        if self.request is None:
            raise TransportException("Can't read without write on legacy Bridge")
        try:
            data = self.transport._call("call", data=self.request)
            return bytes.fromhex(data.text)
        finally:
            self.request = None


class BridgeTransport(Transport):
    """
    BridgeTransport implements transport through TREZOR Bridge (aka trezord).
    """

    PATH_PREFIX = "bridge"
    ENABLED = True

    def __init__(
        self, device: Dict[str, Any], legacy: bool, debug: bool = False
    ) -> None:
        if legacy and debug:
            raise TransportException("Debugging not supported on legacy Bridge")

        self.device = device
        self.session = None  # type: Optional[str]
        self.debug = debug
        self.legacy = legacy

        if legacy:
            self.handle = BridgeHandleLegacy(self)  # type: BridgeHandle
        else:
            self.handle = BridgeHandleModern(self)

    def get_path(self) -> str:
        return "%s:%s" % (self.PATH_PREFIX, self.device["path"])

    def find_debug(self) -> "BridgeTransport":
        if not self.device.get("debug"):
            raise TransportException("Debug device not available")
        return BridgeTransport(self.device, self.legacy, debug=True)

    def _call(self, action: str, data: str = None) -> requests.Response:
        session = self.session or "null"
        uri = action + "/" + str(session)
        if self.debug:
            uri = "debug/" + uri
        return call_bridge(uri, data=data)

    @classmethod
    def enumerate(cls) -> Iterable["BridgeTransport"]:
        try:
            legacy = is_legacy_bridge()
            return [
                BridgeTransport(dev, legacy) for dev in call_bridge("enumerate").json()
            ]
        except Exception:
            return []

    def begin_session(self) -> None:
        data = self._call("acquire/" + self.device["path"])
        self.session = data.json()["session"]

    def end_session(self) -> None:
        if not self.session:
            return
        self._call("release")
        self.session = None

    def write(self, msg: protobuf.MessageType) -> None:
        LOG.debug(
            "sending message: {}".format(msg.__class__.__name__),
            extra={"protobuf": msg},
        )
        buffer = BytesIO()
        protobuf.dump_message(buffer, msg)
        ser = buffer.getvalue()
        header = struct.pack(">HL", mapping.get_type(msg), len(ser))

        self.handle.write_buf(header + ser)

    def read(self) -> protobuf.MessageType:
        data = self.handle.read_buf()
        headerlen = struct.calcsize(">HL")
        msg_type, datalen = struct.unpack(">HL", data[:headerlen])
        buffer = BytesIO(data[headerlen : headerlen + datalen])
        msg = protobuf.load_message(buffer, mapping.get_class(msg_type))
        LOG.debug(
            "received message: {}".format(msg.__class__.__name__),
            extra={"protobuf": msg},
        )
        return msg
