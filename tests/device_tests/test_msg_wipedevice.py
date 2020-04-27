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

from trezorlib import device


@pytest.mark.setup_client(passphrase=True)
def test_wipe_device(client):
    assert client.features.initialized is True
    assert client.features.label == "test"
    assert client.features.passphrase_protection is True
    device_id = client.get_device_id()

    device.wipe(client)

    assert client.features.initialized is False
    assert client.features.label is None
    assert client.features.passphrase_protection is False
    assert client.get_device_id() != device_id
