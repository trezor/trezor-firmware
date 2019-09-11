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

from trezorlib import device, exceptions, messages

from .common import (
    MNEMONIC_SUPERSHAMIR_128BIT,
    MNEMONIC_SUPERSHAMIR_256BIT,
    MNEMONIC_SHAMIR_20_2of3_2of3_GROUPS,
    recovery_enter_shares,
)

pytestmark = pytest.mark.skip_t1

EXTRA_GROUP_SHARE = [
    "gesture negative ceramic leaf device fantasy style ceramic safari keyboard thumb total smug cage plunge aunt favorite lizard intend peanut"
]

# secrets generated using model T
VECTORS = (
    (MNEMONIC_SUPERSHAMIR_128BIT, "c2d2e26ad06023c60145f150abe2dd2b"),
    (
        MNEMONIC_SUPERSHAMIR_256BIT,
        "c41d5cf80fed71a008a3a0ae0458ff0c6d621b1a5522bccbfedbcfad87005c06",
    ),
)


@pytest.mark.parametrize("shares, secret", VECTORS)
@pytest.mark.setup_client(uninitialized=True)
def test_secret(client, shares, secret):
    debug = client.debug

    def input_flow():
        yield  # Confirm Recovery
        debug.press_yes()
        # Proceed with recovery
        yield from recovery_enter_shares(debug, shares, groups=True)

    with client:
        client.set_input_flow(input_flow)
        ret = device.recover(
            client, pin_protection=False, passphrase_protection=False, label="label"
        )

    # Workflow succesfully ended
    assert ret == messages.Success(message="Device recovered")
    assert client.features.initialized is True
    assert client.features.pin_protection is False
    assert client.features.passphrase_protection is False
    assert client.features.backup_type is messages.BackupType.Slip39_Advanced
    assert debug.read_mnemonic_secret().hex() == secret


@pytest.mark.setup_client(uninitialized=True)
def test_extra_share_entered(client):
    debug = client.debug

    def input_flow():
        yield  # Confirm Recovery
        debug.press_yes()
        # Proceed with recovery
        yield from recovery_enter_shares(
            debug, MNEMONIC_SHAMIR_20_2of3_2of3_GROUPS + EXTRA_GROUP_SHARE, groups=True
        )

    with client:
        client.set_input_flow(input_flow)
        ret = device.recover(
            client, pin_protection=False, passphrase_protection=False, label="label"
        )

    # Workflow succesfully ended
    assert ret == messages.Success(message="Device recovered")
    assert client.features.initialized is True
    assert client.features.pin_protection is False
    assert client.features.passphrase_protection is False
    assert client.features.backup_type is messages.BackupType.Slip39_Advanced


@pytest.mark.setup_client(uninitialized=True)
def test_abort(client):
    debug = client.debug

    def input_flow():
        yield  # Confirm Recovery
        debug.press_yes()
        yield  # Homescreen - abort process
        debug.press_no()
        yield  # Homescreen - confirm abort
        debug.press_yes()

    with client:
        client.set_input_flow(input_flow)
        with pytest.raises(exceptions.Cancelled):
            device.recover(client, pin_protection=False, label="label")
        client.init_device()
        assert client.features.initialized is False


@pytest.mark.setup_client(uninitialized=True)
def test_noabort(client):
    debug = client.debug

    def input_flow():
        yield  # Confirm Recovery
        debug.press_yes()
        yield  # Homescreen - abort process
        debug.press_no()
        yield  # Homescreen - go back to process
        debug.press_no()
        yield from recovery_enter_shares(
            debug, EXTRA_GROUP_SHARE + MNEMONIC_SHAMIR_20_2of3_2of3_GROUPS, groups=True
        )

    with client:
        client.set_input_flow(input_flow)
        device.recover(client, pin_protection=False, label="label")
        client.init_device()
        assert client.features.initialized is True
