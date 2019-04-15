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
from unittest import mock

from trezorlib.transport import all_transports
from trezorlib.transport.bridge import BridgeTransport


def test_disabled_transport():
    assert BridgeTransport.ENABLED
    assert BridgeTransport in all_transports()

    BridgeTransport.ENABLED = False
    assert BridgeTransport not in all_transports()
    # re-enable
    BridgeTransport.ENABLED = True


def test_import_all_transports():
    from trezorlib.transport.bridge import BridgeTransport
    from trezorlib.transport.hid import HidTransport
    from trezorlib.transport.webusb import WebUsbTransport
    from trezorlib.transport.udp import UdpTransport

    assert BridgeTransport
    assert HidTransport
    assert WebUsbTransport
    assert UdpTransport


def test_transport_dependencies():
    import trezorlib.transport.hid as hid_transport

    with mock.patch.dict("sys.modules", {"hid": None}):
        importlib.reload(hid_transport)
        assert not hid_transport.HidTransport.ENABLED

    with mock.patch.dict("sys.modules", {"hid": mock.Mock()}):
        importlib.reload(hid_transport)
        assert hid_transport.HidTransport.ENABLED
