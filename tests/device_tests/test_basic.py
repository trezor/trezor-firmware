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

from trezorlib import device, messages


def test_features(client):
    f0 = client.features
    # client erases session_id from its features
    f0.session_id = client.session_id
    f1 = client.call(messages.Initialize(session_id=f0.session_id))
    assert f0 == f1


def test_ping(client):
    ping = client.call(messages.Ping(message="ahoj!"))
    assert ping == messages.Success(message="ahoj!")


def test_device_id_same(client):
    id1 = client.get_device_id()
    client.init_device()
    id2 = client.get_device_id()

    # ID must be at least 12 characters
    assert len(id1) >= 12

    # Every resulf of UUID must be the same
    assert id1 == id2


def test_device_id_different(client):
    id1 = client.get_device_id()
    device.wipe(client)
    id2 = client.get_device_id()

    # Device ID must be fresh after every reset
    assert id1 != id2
