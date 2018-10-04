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

import requests

from . import Transport, TransportException
from .. import mapping, protobuf

LOG = logging.getLogger(__name__)

TREZORD_HOST = "http://127.0.0.1:21325"


class BridgeTransport(Transport):
    """
    BridgeTransport implements transport through TREZOR Bridge (aka trezord).
    """

    PATH_PREFIX = "bridge"
    HEADERS = {"Origin": "https://python.trezor.io"}

    def __init__(self, device):
        super().__init__()

        self.device = device
        self.conn = requests.Session()
        self.session = None
        self.request = None

    def get_path(self):
        return "%s:%s" % (self.PATH_PREFIX, self.device["path"])

    @classmethod
    def _call(cls, action, data=None, uri_suffix=None, session=None):
        if uri_suffix is not None:
            uri_suffix = "/" + uri_suffix
        elif session is not None:
            uri_suffix = "/{}".format(session)
        else:
            uri_suffix = ""

        url = "{}/{}{}".format(TREZORD_HOST, action, uri_suffix)
        r = requests.post(url, headers=cls.HEADERS, data=data)

        if r.status_code != 200:
            raise TransportException(
                "trezord: '{}' action failed with code {}: {}".format(
                    action, r.status_code, r.json().get("error", "(no error message)")
                )
            )
        return r

    @classmethod
    def enumerate(cls):
        try:
            r = cls._call("enumerate")
            return [BridgeTransport(dev) for dev in r.json()]
        except Exception:
            return []

    def open(self):
        r = self._call("acquire", uri_suffix="{}/null".format(self.device["path"]))
        self.session = r.json()["session"]

    def close(self):
        if not self.session:
            return
        self._call("release", session=self.session)
        self.session = None

    def write(self, msg):
        if self.request is not None:
            raise TransportException("trezord can't perform two writes without a read")

        LOG.debug(
            "preparing message: {}".format(msg.__class__.__name__),
            extra={"protobuf": msg},
        )
        # encode the message
        data = BytesIO()
        protobuf.dump_message(data, msg)
        ser = data.getvalue()
        header = struct.pack(">HL", mapping.get_type(msg), len(ser))
        # store for later
        self.request = (header + ser).hex()

    def read(self):
        if self.request is None:
            raise TransportException("trezord: no request in queue")

        try:
            LOG.debug("sending prepared message")
            r = self._call("call", data=self.request, session=self.session)

            data = bytes.fromhex(r.text)
            headerlen = struct.calcsize(">HL")
            msg_type, datalen = struct.unpack(">HL", data[:headerlen])
            data = BytesIO(data[headerlen : headerlen + datalen])
            msg = protobuf.load_message(data, mapping.get_class(msg_type))
            LOG.debug(
                "received message: {}".format(msg.__class__.__name__),
                extra={"protobuf": msg},
            )
            return msg
        finally:
            self.request = None


TRANSPORT = BridgeTransport
