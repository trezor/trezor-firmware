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

from trezorlib import debuglink, device
from trezorlib.exceptions import TrezorFailure
from trezorlib.messages import SdProtectOperationType as Op

from ..common import MNEMONIC12

pytestmark = [pytest.mark.skip_t1, pytest.mark.sd_card]


def test_enable_disable(client):
    assert client.features.sd_protection is False
    # Disabling SD protection should fail
    with pytest.raises(TrezorFailure):
        device.sd_protect(client, Op.DISABLE)

    # Enable SD protection
    device.sd_protect(client, Op.ENABLE)
    assert client.features.sd_protection is True

    # Enabling SD protection should fail
    with pytest.raises(TrezorFailure):
        device.sd_protect(client, Op.ENABLE)
    assert client.features.sd_protection is True

    # Disable SD protection
    device.sd_protect(client, Op.DISABLE)
    assert client.features.sd_protection is False


def test_refresh(client):
    assert client.features.sd_protection is False
    # Enable SD protection
    device.sd_protect(client, Op.ENABLE)
    assert client.features.sd_protection is True

    # Refresh SD protection
    device.sd_protect(client, Op.REFRESH)
    assert client.features.sd_protection is True

    # Disable SD protection
    device.sd_protect(client, Op.DISABLE)
    assert client.features.sd_protection is False

    # Refreshing SD protection should fail
    with pytest.raises(TrezorFailure):
        device.sd_protect(client, Op.REFRESH)
    assert client.features.sd_protection is False


def test_wipe(client):
    # Enable SD protection
    device.sd_protect(client, Op.ENABLE)
    assert client.features.sd_protection is True

    # Wipe device (this wipes internal storage)
    device.wipe(client)
    assert client.features.sd_protection is False

    # Restore device to working status
    debuglink.load_device(
        client, mnemonic=MNEMONIC12, pin=None, passphrase_protection=False, label="test"
    )
    assert client.features.sd_protection is False

    # Enable SD protection
    device.sd_protect(client, Op.ENABLE)
    assert client.features.sd_protection is True

    # Refresh SD protection
    device.sd_protect(client, Op.REFRESH)
