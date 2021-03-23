# This file is part of the Trezor project.
#
# Copyright (C) 2012-2019 SatoshiLabs and contributors
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
import socket
import time
from typing import Iterable, Optional, cast

from ..log import DUMP_PACKETS
from . import TransportException
from .protocol import ProtocolBasedTransport, ProtocolV1

SOCKET_TIMEOUT = 10
TRY_PATH_TIMEOUT = 1

LOG = logging.getLogger(__name__)


class UdpTransport(ProtocolBasedTransport):

    DEFAULT_HOST = "127.0.0.1"
    DEFAULT_PORT = 21324
    PATH_PREFIX = "udp"
    ENABLED = True

    def __init__(self, device: str = None) -> None:
        if not device:
            host = UdpTransport.DEFAULT_HOST
            port = UdpTransport.DEFAULT_PORT
        else:
            devparts = device.split(":")
            host = devparts[0]
            port = int(devparts[1]) if len(devparts) > 1 else UdpTransport.DEFAULT_PORT
        self.device = (host, port)
        self.socket: Optional[socket.socket] = None

        super().__init__(protocol=ProtocolV1(self))

    def get_path(self) -> str:
        return "{}:{}:{}".format(self.PATH_PREFIX, *self.device)

    def find_debug(self) -> "UdpTransport":
        host, port = self.device
        return UdpTransport("{}:{}".format(host, port + 1))

    @classmethod
    def _try_path(cls, path: str) -> "UdpTransport":
        d = cls(path)
        try:
            d.wait_until_ready(timeout=TRY_PATH_TIMEOUT)
            return d
        except Exception as e:
            raise TransportException(
                "No Trezor device found at address {}".format(d.get_path())
            ) from e

    @classmethod
    def enumerate(cls) -> Iterable["UdpTransport"]:
        default_path = "{}:{}".format(cls.DEFAULT_HOST, cls.DEFAULT_PORT)
        try:
            return [cls._try_path(default_path)]
        except TransportException:
            return []

    @classmethod
    def find_by_path(cls, path: str, prefix_search: bool = False) -> "UdpTransport":
        if prefix_search:
            return cast(UdpTransport, super().find_by_path(path, prefix_search))
            # This is *technically* type-able: mark `find_by_path` as returning
            # the same type from which `cls` comes from.
            # Mypy can't handle that though, so here we are.
        else:
            path = path.replace("{}:".format(cls.PATH_PREFIX), "")
            return cls._try_path(path)

    def wait_until_ready(self, timeout: float = 10) -> None:
        try:
            self.open()
            self.socket.settimeout(0)
            start = time.monotonic()
            while True:
                if self._ping():
                    break
                elapsed = time.monotonic() - start
                if elapsed >= timeout:
                    raise TransportException("Timed out waiting for connection.")

                time.sleep(0.05)
        finally:
            self.close()

    def open(self) -> None:
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.connect(self.device)
        self.socket.settimeout(SOCKET_TIMEOUT)

    def close(self) -> None:
        if self.socket is not None:
            self.socket.close()
        self.socket = None

    def _ping(self) -> bool:
        """Test if the device is listening."""
        assert self.socket is not None
        resp = None
        try:
            self.socket.sendall(b"PINGPING")
            resp = self.socket.recv(8)
        except Exception:
            pass
        return resp == b"PONGPONG"

    def write_chunk(self, chunk: bytes) -> None:
        assert self.socket is not None
        if len(chunk) != 64:
            raise TransportException("Unexpected data length")
        LOG.log(DUMP_PACKETS, "sending packet: {}".format(chunk.hex()))
        self.socket.sendall(chunk)

    def read_chunk(self) -> bytes:
        assert self.socket is not None
        while True:
            try:
                chunk = self.socket.recv(64)
                break
            except socket.timeout:
                continue
        LOG.log(DUMP_PACKETS, "received packet: {}".format(chunk.hex()))
        if len(chunk) != 64:
            raise TransportException("Unexpected chunk size: %d" % len(chunk))
        return bytearray(chunk)
