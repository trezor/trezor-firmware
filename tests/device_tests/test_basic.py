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

import pytest

from trezorlib import messages, models
from trezorlib.client import get_client
from trezorlib.debuglink import DebugSession as Session
from trezorlib.debuglink import TrezorTestContext as Client

from ..click_tests.device_menu.common import open_device_menu


def test_capabilities(session: Session):
    assert (messages.Capability.Translations in session.features.capabilities) == (
        session.model is not models.T1B1
    )
    assert (messages.Capability.BLE in session.features.capabilities) == (
        session.model is models.T3W1
    )


def test_ping(session: Session):
    ping = session.call(messages.Ping(message="ahoj!"))
    assert ping == messages.Success(message="ahoj!")


def test_device_id_same(client: Client):
    id1 = client.features.device_id
    client.refresh_features()
    id2 = client.features.device_id

    # ID must be at least 12 characters
    assert len(id1) >= 12

    # Every result of UUID must be the same
    assert id1 == id2


def test_device_id_different(client: Client):
    # Device id is pre-configured in storage when we get it.
    # Depending on when exactly we reseed (for ui test consistency purposes),
    # we may or may not generate the same device id from the same randomness.
    #
    # To avoid the problem, this test and similar that depend on device id
    # must explicitly wipe at start.
    client.wipe_device(reseed=True)
    id1 = client.features.device_id
    client.wipe_device(reseed=False)
    id2 = client.features.device_id

    # Device ID must be fresh after every reset
    assert id1 != id2


@pytest.mark.setup_client(uninitialized=True)
def test_not_initialized(session: Session):
    resp = session.call_raw(messages.GetPublicKey(address_n=[0]))
    resp = messages.Failure.ensure_isinstance(resp)
    expected = (
        messages.FailureType.NotInitialized,
        messages.FailureType.InvalidSession,
    )
    assert resp.code == expected[session.test_ctx.is_thp()]


@pytest.mark.protocol("v1")
def test_desync_v1(client: Client):
    with client.get_session(passphrase=None) as session:
        resp = session.call_raw(messages.Ping(message="test", button_protection=True))
        messages.ButtonRequest.ensure_isinstance(resp)
        session.write(messages.ButtonAck())
        session.debug.press_no()
        # don't read the response - simulating host disconnection

    # Creating a new client fails without skipping stale responses
    # (see https://github.com/trezor/trezor-firmware/issues/6859)
    get_client(client.app, client.transport).ping("reconnect")


@pytest.mark.models("eckhart")
def test_get_features_avoids_restart(session: Session):
    debug = session.debug
    assert "Homescreen" == debug.read_layout().main_component()
    open_device_menu(debug)
    assert "DeviceMenuScreen" == debug.read_layout().main_component()

    # GetFeatures doesn't restart MicroPython event loop - device menu is still open.
    session.refresh_features()
    assert "DeviceMenuScreen" == debug.read_layout().main_component()
