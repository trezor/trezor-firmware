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

from trezorlib import messages, models
from trezorlib.debuglink import DebugSession as Session
from trezorlib.debuglink import TrezorTestContext as Client


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
