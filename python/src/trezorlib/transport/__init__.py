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
import typing as t

from ..exceptions import TrezorException

if t.TYPE_CHECKING:
    from ..models import TrezorModel

    T = t.TypeVar("T", bound="Transport")


LOG = logging.getLogger(__name__)

UDEV_RULES_STR = """
Do you have udev rules installed?
https://github.com/trezor/trezor-common/blob/master/udev/51-trezor.rules
""".strip()


MessagePayload = t.Tuple[int, bytes]


class TransportException(TrezorException):
    pass


class DeviceIsBusy(TransportException):
    pass


class Timeout(TransportException):
    pass


class Transport:
    PATH_PREFIX: str

    @classmethod
    def enumerate(
        cls: t.Type[T], models: t.Iterable[TrezorModel] | None = None
    ) -> t.Iterable[T]:
        raise NotImplementedError

    @classmethod
    def find_by_path(cls: t.Type[T], path: str, prefix_search: bool = False) -> T:
        for device in cls.enumerate():

            if device.get_path() == path:
                return device

            if prefix_search and device.get_path().startswith(path):
                return device

        raise TransportException(f"{cls.PATH_PREFIX} device not found: {path}")

    def get_path(self) -> str:
        raise NotImplementedError

    def find_debug(self: T) -> T:
        raise NotImplementedError

    def open(self) -> None:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError

    def write_chunk(self, chunk: bytes) -> None:
        raise NotImplementedError

    def read_chunk(self, timeout: float | None = None) -> bytes:
        raise NotImplementedError

    def ping(self) -> bool:
        raise NotImplementedError

    CHUNK_SIZE: t.ClassVar[int | None]


def all_transports() -> t.Iterable[t.Type["Transport"]]:
    from .bridge import BridgeTransport
    from .hid import HidTransport
    from .udp import UdpTransport
    from .webusb import WebUsbTransport

    transports: t.Tuple[t.Type["Transport"], ...] = (
        BridgeTransport,
        HidTransport,
        UdpTransport,
        WebUsbTransport,
    )
    return set(t for t in transports if t.ENABLED)


def enumerate_devices(
    models: t.Iterable[TrezorModel] | None = None,
) -> t.Sequence[Transport]:
    devices: t.List[Transport] = []
    for transport in all_transports():
        name = transport.__name__
        try:
            found = list(transport.enumerate(models))
            LOG.info(f"Enumerating {name}: found {len(found)} devices")
            devices.extend(found)
        except NotImplementedError:
            LOG.error(f"{name} does not implement device enumeration")
        except Exception as e:
            excname = e.__class__.__name__
            LOG.error(f"Failed to enumerate {name}. {excname}: {e}")
    return devices


def get_transport(path: str | None = None, prefix_search: bool = False) -> Transport:
    if path is None:
        try:
            return next(iter(enumerate_devices()))
        except StopIteration:
            raise TransportException("No Trezor device found") from None

    # Find whether B is prefix of A (transport name is part of the path)
    # or A is prefix of B (path is a prefix, or a name, of transport).
    # This naively expects that no two transports have a common prefix.
    def match_prefix(a: str, b: str) -> bool:
        return a.startswith(b) or b.startswith(a)

    LOG.info(
        "looking for device by {}: {}".format(
            "prefix" if prefix_search else "full path", path
        )
    )
    transports = [t for t in all_transports() if match_prefix(path, t.PATH_PREFIX)]
    if transports:
        return transports[0].find_by_path(path, prefix_search=prefix_search)

    raise TransportException(f"Could not find device by path: {path}")
