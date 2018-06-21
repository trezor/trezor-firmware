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

import importlib
import logging

from typing import Iterable, Type, List, Set

LOG = logging.getLogger(__name__)


class TransportException(Exception):
    pass


class Transport(object):

    def __init__(self):
        self.session_counter = 0

    def __str__(self):
        return self.get_path()

    def get_path(self):
        return '{}:{}'.format(self.PATH_PREFIX, self.device)

    def session_begin(self):
        if self.session_counter == 0:
            self.open()
        self.session_counter += 1

    def session_end(self):
        self.session_counter = max(self.session_counter - 1, 0)
        if self.session_counter == 0:
            self.close()

    def open(self):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError

    @classmethod
    def enumerate(cls):
        raise NotImplementedError

    @classmethod
    def find_by_path(cls, path, prefix_search=False):
        for device in cls.enumerate():
            if path is None or device.get_path() == path \
                    or (prefix_search and device.get_path().startswith(path)):
                return device

        raise TransportException('{} device not found: {}'.format(cls.PATH_PREFIX, path))


def all_transports() -> Iterable[Type[Transport]]:
    transports = set()  # type: Set[Type[Transport]]
    for modname in ("bridge", "hid", "udp", "webusb"):
        try:
            # Import the module and find the Transport class.
            # To avoid iterating over every item, the module should assign its Transport class
            # to a constant named TRANSPORT.
            module = importlib.import_module("." + modname, __name__)
            try:
                transports.add(getattr(module, "TRANSPORT"))
            except AttributeError:
                LOG.warning("Skipping broken module {}".format(modname))
        except ImportError as e:
            LOG.info("Failed to import module {}: {}".format(modname, e))

    return transports


def enumerate_devices() -> Iterable[Transport]:
    devices = []  # type: List[Transport]
    for transport in all_transports():
        try:
            found = transport.enumerate()
            LOG.info("Enumerating {}: found {} devices".format(transport.__name__, len(found)))
            devices.extend(found)
        except NotImplementedError:
            LOG.error("{} does not implement device enumeration".format(transport.__name__))
        except Exception as e:
            LOG.error("Failed to enumerate {}. {}: {}".format(transport.__name__, e.__class__.__name__, e))
    return devices


def get_transport(path: str = None, prefix_search: bool = False) -> Transport:
    if path is None:
        try:
            return next(iter(enumerate_devices()))
        except IndexError:
            raise Exception("No TREZOR device found") from None

    # Find whether B is prefix of A (transport name is part of the path)
    # or A is prefix of B (path is a prefix, or a name, of transport).
    # This naively expects that no two transports have a common prefix.
    def match_prefix(a: str, b: str) -> bool:
        return a.startswith(b) or b.startswith(a)

    LOG.info("looking for device by {}: {}".format("prefix" if prefix_search else "full path", path))
    transports = [t for t in all_transports() if match_prefix(path, t.PATH_PREFIX)]
    if transports:
        return transports[0].find_by_path(path, prefix_search=prefix_search)

    raise Exception("Could not find device by path: {}".format(path))
