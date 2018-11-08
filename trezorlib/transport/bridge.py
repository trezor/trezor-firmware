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

import binascii
import logging
import struct
from io import BytesIO
from typing import Any, Dict, Iterable

import requests

from . import Transport, TransportException
from .. import mapping, protobuf

LOG = logging.getLogger(__name__)

TREZORD_HOST = "http://127.0.0.1:21325"


def get_error(resp: requests.Response) -> str:
    return " (error=%d str=%s)" % (resp.status_code, resp.json()["error"])


class BridgeTransport(Transport):
    """
    BridgeTransport implements transport through TREZOR Bridge (aka trezord).
    """

    PATH_PREFIX = "bridge"
    HEADERS = {"Origin": "https://python.trezor.io"}

    def __init__(self, device: Dict[str, Any]) -> None:
        self.device = device
        self.conn = requests.Session()
        self.session = None  # type: Optional[str]
        self.response = None  # type: Optional[str]

    def get_path(self) -> str:
        return "%s:%s" % (self.PATH_PREFIX, self.device["path"])

    @classmethod
    def enumerate(cls) -> Iterable["BridgeTransport"]:
        try:
            r = requests.post(TREZORD_HOST + "/enumerate", headers=cls.HEADERS)
            if r.status_code != 200:
                raise TransportException(
                    "trezord: Could not enumerate devices" + get_error(r)
                )
            return [BridgeTransport(dev) for dev in r.json()]
        except Exception:
            return []

    def begin_session(self) -> None:
        r = self.conn.post(
            TREZORD_HOST + "/acquire/%s/null" % self.device["path"],
            headers=self.HEADERS,
        )
        if r.status_code != 200:
            raise TransportException(
                "trezord: Could not acquire session" + get_error(r)
            )
        self.session = r.json()["session"]

    def end_session(self) -> None:
        if not self.session:
            return
        r = self.conn.post(
            TREZORD_HOST + "/release/%s" % self.session, headers=self.HEADERS
        )
        if r.status_code != 200:
            raise TransportException(
                "trezord: Could not release session" + get_error(r)
            )
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
        data = binascii.hexlify(header + ser).decode()
        r = self.conn.post(  # type: ignore  # typeshed bug
            TREZORD_HOST + "/call/%s" % self.session, data=data, headers=self.HEADERS
        )
        if r.status_code != 200:
            raise TransportException("trezord: Could not write message" + get_error(r))
        self.response = r.text

    def read(self) -> protobuf.MessageType:
        if self.response is None:
            raise TransportException("No response stored")
        data = binascii.unhexlify(self.response)
        headerlen = struct.calcsize(">HL")
        (msg_type, datalen) = struct.unpack(">HL", data[:headerlen])
        buffer = BytesIO(data[headerlen : headerlen + datalen])
        msg = protobuf.load_message(buffer, mapping.get_class(msg_type))
        LOG.debug(
            "received message: {}".format(msg.__class__.__name__),
            extra={"protobuf": msg},
        )
        self.response = None
        return msg


TRANSPORT = BridgeTransport
