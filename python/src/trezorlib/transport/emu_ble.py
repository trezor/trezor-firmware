# This file is part of the Trezor project.
#
# Copyright (C) 2025 SatoshiLabs and contributors
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
from enum import Enum
from typing import TYPE_CHECKING, Iterable, Tuple

import construct as c
from construct_classes import Struct

from ..log import DUMP_PACKETS
from ..tools import EnumAdapter
from . import Timeout, Transport, TransportException
from .udp import UdpTransport

if TYPE_CHECKING:
    from ..models import TrezorModel

SOCKET_TIMEOUT = 0.1

LOG = logging.getLogger(__name__)


class EventType(Enum):
    NONE = 0
    CONNECTED = 1
    DISCONNECTED = 2
    PAIRING_REQUEST = 3
    PAIRING_CANCELLED = 4
    EMULATOR_PING = 255


class CommandType(Enum):
    SWITCH_OFF = 0
    SWITCH_ON = 1
    PAIRING_MODE = 2
    DISCONNECT = 3
    ERASE_BONDS = 4
    ALLOW_PAIRING = 5
    REJECT_PAIRING = 6
    EMULATOR_PONG = 255


class Event(Struct):
    event_type: EventType
    connection_id: int
    data: bytes

    # fmt: off
    SUBCON = c.Struct(
        "event_type" / EnumAdapter(c.Int32ul, EventType),
        "connection_id" / c.Int32ul,
        "data" / c.Prefixed(c.Int8ul, c.GreedyBytes),
    )
    # fmt: on

    @staticmethod
    def new(
        event_type: EventType, connection_id: int = 0, data: bytes | None = None
    ) -> Event:
        return Event(
            event_type=event_type, connection_id=connection_id, data=data or bytes()
        )

    @staticmethod
    def ping() -> Event:
        return Event.new(EventType.EMULATOR_PING)


class Command(Struct):
    command_type: CommandType
    data_len: int
    raw: bytes  # TODO parse advertising data

    # fmt: off
    SUBCON = c.Struct(
        "command_type" / EnumAdapter(c.Int32ul, CommandType),
        "data_len" / c.Int8ul,
        "raw" / c.Bytes(32),
    )
    # fmt: on


# You should probably use bluez-emu-brige instead of this transport directly
# as it does not implement any BLE connection management logic.
class EmuBleTransport(Transport):

    DEFAULT_HOST = "127.0.0.1"
    DEFAULT_PORT = 21328
    PATH_PREFIX = "emuble"
    ENABLED: bool = False
    CHUNK_SIZE = 244

    def __init__(self, device: str | None = None) -> None:
        if not device:
            host = EmuBleTransport.DEFAULT_HOST
            port = EmuBleTransport.DEFAULT_PORT
        else:
            devparts = device.split(":")
            host = devparts[0]
            port = (
                int(devparts[1]) if len(devparts) > 1 else EmuBleTransport.DEFAULT_PORT
            )
        self.device: Tuple[str, int] = (host, port)

        self.data_socket: socket.socket | None = None
        self.event_socket: socket.socket | None = None
        super().__init__()

    @classmethod
    def _try_path(cls, path: str) -> "EmuBleTransport":
        d = cls(path)
        try:
            d.open()
            if d.ping():
                return d
            else:
                raise TransportException(
                    f"No Trezor device found at address {d.get_path()}"
                )
        except Exception as e:
            raise
            raise TransportException(f"Error opening {d.get_path()}") from e

        finally:
            d.close()

    @classmethod
    def enumerate(
        cls, _models: Iterable["TrezorModel"] | None = None
    ) -> Iterable["EmuBleTransport"]:
        default_path = f"{cls.DEFAULT_HOST}:{cls.DEFAULT_PORT}"
        try:
            return [cls._try_path(default_path)]
        except TransportException:
            return []

    @classmethod
    def find_by_path(cls, path: str, prefix_search: bool = False) -> "EmuBleTransport":
        try:
            address = path.replace(f"{cls.PATH_PREFIX}:", "")
            return cls._try_path(address)
        except TransportException:
            if not prefix_search:
                raise

        assert prefix_search  # otherwise we would have raised above
        return super().find_by_path(path, prefix_search)

    def get_path(self) -> str:
        return "{}:{}:{}".format(self.PATH_PREFIX, *self.device)

    def open(self) -> None:
        try:
            self.data_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.data_socket.connect(self.device)
            self.data_socket.settimeout(SOCKET_TIMEOUT)
            self.event_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.event_socket.connect((self.device[0], self.device[1] + 1))
            self.event_socket.settimeout(SOCKET_TIMEOUT)
        except Exception:
            self.close()
            raise

    def close(self) -> None:
        if self.data_socket is not None:
            self.data_socket.close()
            self.data_socket = None
        if self.event_socket is not None:
            self.event_socket.close()
            self.event_socket = None

    def write_chunk(self, chunk: bytes) -> None:
        assert self.data_socket is not None
        if len(chunk) != self.CHUNK_SIZE:
            raise TransportException("Unexpected data length")
        LOG.log(DUMP_PACKETS, f"sending packet: {chunk.hex()}")
        self.data_socket.sendall(chunk)

    def read_chunk(self, timeout: float | None = None) -> bytes:
        assert self.data_socket is not None
        start = time.time()
        while True:
            try:
                chunk = self.data_socket.recv(64)
                break
            except socket.timeout:
                if timeout is not None and time.time() - start > timeout:
                    raise Timeout(f"Timeout reading UDP packet ({timeout}s)")
        LOG.log(DUMP_PACKETS, f"received packet: {chunk.hex()}")
        if len(chunk) != 64:
            raise TransportException(f"Unexpected chunk size: {len(chunk)}")
        return bytearray(chunk)

    def find_debug(self) -> "UdpTransport":
        host, port = self.device
        return UdpTransport(f"{host}:{port - 3}")

    def wait_until_ready(self, timeout: float = 10) -> None:
        try:
            self.open()
            start = time.monotonic()
            while True:
                if self.ping():
                    break
                elapsed = time.monotonic() - start
                if elapsed >= timeout:
                    raise Timeout("Timed out waiting for connection.")

                time.sleep(0.05)
        finally:
            self.close()

    def ping(self) -> bool:
        """Test if the device is listening."""
        assert self.event_socket is not None
        resp = None
        try:
            self.event_socket.sendall(Event.ping().build())
            resp = self.read_command()
        except Exception:
            pass
        return (resp is not None) and (resp.command_type == CommandType.EMULATOR_PONG)

    def ble_connected(self) -> None:
        assert self.event_socket is not None
        self.event_socket.sendall(Event.new(EventType.CONNECTED).build())

    def ble_disconnected(self) -> None:
        assert self.event_socket is not None
        self.event_socket.sendall(Event.new(EventType.DISCONNECTED).build())

    def ble_pairing_request(self, pairing_code: bytes) -> None:
        assert self.event_socket is not None
        assert len(pairing_code) == 6
        self.event_socket.sendall(
            Event.new(EventType.PAIRING_REQUEST, data=pairing_code).build()
        )

    def ble_pairing_cancel(self) -> None:
        assert self.event_socket is not None
        self.event_socket.sendall(Event.new(EventType.PAIRING_CANCELLED).build())

    def read_command(self) -> Command | None:
        assert self.event_socket is not None
        try:
            data = self.event_socket.recv(64)
        except TimeoutError:
            return None
        return Command.parse(data)
