# This file is part of the Trezor project.
#
# Copyright (C) SatoshiLabs and contributors
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
import socket
import time

LOG = logging.getLogger(__name__)


class VcpUdpTransport:
    CHUNK_SIZE = 64

    def __init__(self, port: int, host: str = "127.0.0.1") -> None:
        self.port = port
        self.host = host
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(1.0)
        self._buf = b""

    def readline(self, timeout: float) -> str:
        deadline = time.monotonic() + timeout
        while True:
            # Check buffer first
            if b"\n" in self._buf:
                line, self._buf = self._buf.split(b"\n", 1)
                return line.decode("utf-8", errors="replace").strip()

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError()

            self.socket.settimeout(min(remaining, 1.0))
            try:
                data, _ = self.socket.recvfrom(4096)
                self._buf += data
            except socket.timeout:
                continue

    def writeline(self, line: str) -> None:
        data = (line + "\r").encode("utf-8")
        for i in range(0, len(data), self.CHUNK_SIZE):
            self.socket.sendto(data[i : i + self.CHUNK_SIZE], (self.host, self.port))
        LOG.debug(">>> %s", line)

    def close(self) -> None:
        self.socket.close()
