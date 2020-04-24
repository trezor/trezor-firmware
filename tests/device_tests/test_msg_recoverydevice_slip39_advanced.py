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

from ..common import (
    MNEMONIC_SLIP39_ADVANCED_20,
    MNEMONIC_SLIP39_ADVANCED_33,
    recovery_enter_shares,
)

pytestmark = pytest.mark.skip_t1

EXTRA_GROUP_SHARE = [
    "eraser senior decision smug corner ruin rescue cubic angel tackle skin skunk program roster trash rumor slush angel flea amazing"
]

# secrets generated using model T
VECTORS = (
    (MNEMONIC_SLIP39_ADVANCED_20, "c2d2e26ad06023c60145f150abe2dd2b"),
    (
        MNEMONIC_SLIP39_ADVANCED_33,
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
    assert debug.state().mnemonic_secret.hex() == secret


@pytest.mark.setup_client(uninitialized=True)
def test_extra_share_entered(client):
    debug = client.debug

    def input_flow():
        yield  # Confirm Recovery
        debug.press_yes()
        # Proceed with recovery
        yield from recovery_enter_shares(
            debug, EXTRA_GROUP_SHARE + MNEMONIC_SLIP39_ADVANCED_20, groups=True
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
            debug, EXTRA_GROUP_SHARE + MNEMONIC_SLIP39_ADVANCED_20, groups=True
        )

    with client:
        client.set_input_flow(input_flow)
        device.recover(client, pin_protection=False, label="label")
        client.init_device()
        assert client.features.initialized is True


@pytest.mark.setup_client(uninitialized=True)
def test_same_share(client):
    debug = client.debug
    # we choose the second share from the fixture because
    # the 1st is 1of1 and group threshold condition is reached first
    first_share = MNEMONIC_SLIP39_ADVANCED_20[1].split(" ")
    # second share is first 4 words of first
    second_share = MNEMONIC_SLIP39_ADVANCED_20[1].split(" ")[:4]

    def input_flow():
        yield  # Confirm Recovery
        debug.press_yes()
        yield  # Homescreen - start process
        debug.press_yes()
        yield  # Enter number of words
        debug.input(str(len(first_share)))
        yield  # Homescreen - proceed to share entry
        debug.press_yes()
        yield  # Enter first share
        for word in first_share:
            debug.input(word)

        yield  # Continue to next share
        debug.press_yes()
        yield  # Homescreen - next share
        debug.press_yes()
        yield  # Enter next share
        for word in second_share:
            debug.input(word)

        code = yield
        assert code == messages.ButtonRequestType.Warning

        client.cancel()

    with client:
        client.set_input_flow(input_flow)
        with pytest.raises(exceptions.Cancelled):
            device.recover(client, pin_protection=False, label="label")


@pytest.mark.setup_client(uninitialized=True)
def test_group_threshold_reached(client):
    debug = client.debug
    # first share in the fixture is 1of1 so we choose that
    first_share = MNEMONIC_SLIP39_ADVANCED_20[0].split(" ")
    # second share is first 3 words of first
    second_share = MNEMONIC_SLIP39_ADVANCED_20[0].split(" ")[:3]

    def input_flow():
        yield  # Confirm Recovery
        debug.press_yes()
        yield  # Homescreen - start process
        debug.press_yes()
        yield  # Enter number of words
        debug.input(str(len(first_share)))
        yield  # Homescreen - proceed to share entry
        debug.press_yes()
        yield  # Enter first share
        for word in first_share:
            debug.input(word)

        yield  # Continue to next share
        debug.press_yes()
        yield  # Homescreen - next share
        debug.press_yes()
        yield  # Enter next share
        for word in second_share:
            debug.input(word)

        code = yield
        assert code == messages.ButtonRequestType.Warning

        client.cancel()

    with client:
        client.set_input_flow(input_flow)
        with pytest.raises(exceptions.Cancelled):
            device.recover(client, pin_protection=False, label="label")
