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

from trezorlib import device, messages
from trezorlib.exceptions import TrezorFailure

from ..common import recovery_enter_shares

pytestmark = pytest.mark.skip_t1

SHARES_20_2of3 = [
    "crush merchant academic acid dream decision orbit smug trend trust painting slice glad crunch veteran lunch friar satoshi engage aquatic",
    "crush merchant academic agency devote eyebrow disaster island deploy flip toxic budget numerous airport loyalty fitness resident learn sympathy daughter",
    "crush merchant academic always course verdict rescue paces fridge museum energy solution space ladybug junction national biology game fawn coal",
]

INVALID_SHARES_20_2of3 = [
    "gesture necklace academic acid civil round fiber buyer swing ancient jerky kitchen chest dining enjoy tension museum increase various rebuild",
    "gesture necklace academic agency decrease justice ounce dragon shaped unknown material answer dress wrote smell family squeeze diet angry husband",
]


@pytest.mark.setup_client(mnemonic=SHARES_20_2of3[0:2], passphrase=True)
def test_2of3_dryrun(client):
    debug = client.debug

    def input_flow():
        yield  # Confirm Dryrun
        debug.press_yes()
        # run recovery flow
        yield from recovery_enter_shares(debug, SHARES_20_2of3[1:3])

    with client:
        client.set_input_flow(input_flow)
        ret = device.recover(
            client,
            passphrase_protection=False,
            pin_protection=False,
            label="label",
            language="en-US",
            dry_run=True,
        )

    # Dry run was successful
    assert ret == messages.Success(
        message="The seed is valid and matches the one in the device"
    )


@pytest.mark.setup_client(mnemonic=SHARES_20_2of3[0:2], passphrase=True)
def test_2of3_invalid_seed_dryrun(client):
    debug = client.debug

    def input_flow():
        yield  # Confirm Dryrun
        debug.press_yes()
        # run recovery flow
        yield from recovery_enter_shares(debug, INVALID_SHARES_20_2of3)

    # test fails because of different seed on device
    with client, pytest.raises(
        TrezorFailure, match=r"The seed does not match the one in the device"
    ):
        client.set_input_flow(input_flow)
        device.recover(
            client,
            passphrase_protection=False,
            pin_protection=False,
            label="label",
            language="en-US",
            dry_run=True,
        )
