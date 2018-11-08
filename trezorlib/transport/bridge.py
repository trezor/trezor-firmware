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
from typing import Any, Dict, Iterable

import requests

from . import Transport, TransportException
from .. import mapping, protobuf

LOG = logging.getLogger(__name__)

TREZORD_HOST = "http://127.0.0.1:21325"
TREZORD_ORIGIN_HEADER = {"Origin": "https://python.trezor.io"}

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


class BridgeTransport(Transport):
    """
    BridgeTransport implements transport through TREZOR Bridge (aka trezord).
    """

    PATH_PREFIX = "bridge"

    def __init__(self, device: Dict[str, Any]) -> None:
        self.device = device
        self.session = None  # type: Optional[str]
        self.request = None  # type: Optional[str]
        self.debug = False

    def get_path(self) -> str:
        return "%s:%s" % (self.PATH_PREFIX, self.device["path"])

    @classmethod
    def enumerate(cls) -> Iterable["BridgeTransport"]:
        try:
            return [BridgeTransport(dev) for dev in call_bridge("enumerate").json()]
        except Exception:
            return []

    def _call(self, action: str, data: str = None) -> requests.Response:
        session = self.session or "null"
        uri = action + "/" + str(session)
        return call_bridge(uri, data=data)

    def begin_session(self) -> None:
        LOG.debug("acquiring session from {}".format(self.session))
        data = self._call("acquire/" + self.device["path"])
        self.session = data.json()["session"]
        LOG.debug("acquired session {}".format(self.session))

    def end_session(self) -> None:
        LOG.debug("releasing session {}".format(self.session))
        if not self.session:
            return
        self._call("release")
        self.session = None

    def write(self, msg: protobuf.MessageType) -> None:
        if self.request is not None:
            raise TransportException("Cannot enqueue two requests")

        LOG.debug(
            "sending message: {}".format(msg.__class__.__name__),
            extra={"protobuf": msg},
        )
        buffer = BytesIO()
        protobuf.dump_message(buffer, msg)
        ser = buffer.getvalue()
        header = struct.pack(">HL", mapping.get_type(msg), len(ser))

        self.request = (header + ser).hex()

    def read(self) -> protobuf.MessageType:
        if self.request is None:
            raise TransportException("No request stored")

        try:
            data = bytes.fromhex(self._call("call", data=self.request).text)
            headerlen = struct.calcsize(">HL")
            msg_type, datalen = struct.unpack(">HL", data[:headerlen])
            buffer = BytesIO(data[headerlen : headerlen + datalen])
            msg = protobuf.load_message(buffer, mapping.get_class(msg_type))
            LOG.debug(
                "received message: {}".format(msg.__class__.__name__),
                extra={"protobuf": msg},
            )
            return msg
        finally:
            self.request = None


TRANSPORT = BridgeTransport
