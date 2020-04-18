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

from ..common import MNEMONIC_SLIP39_ADVANCED_20, recovery_enter_shares

pytestmark = pytest.mark.skip_t1

INVALID_SHARES_SLIP39_ADVANCED_20 = [
    "chest garlic acrobat leaf diploma thank soul predator grant laundry camera license language likely slim twice amount rich total carve",
    "chest garlic acrobat lily adequate dwarf genius wolf faint nylon scroll national necklace leader pants literary lift axle watch midst",
    "chest garlic beard leaf coastal album dramatic learn identify angry dismiss goat plan describe round writing primary surprise sprinkle orbit",
    "chest garlic beard lily burden pistol retreat pickup emphasis large gesture hand eyebrow season pleasure genuine election skunk champion income",
]

# Extra share from another group to make sure it does not matter.
EXTRA_GROUP_SHARE = [
    "eraser senior decision smug corner ruin rescue cubic angel tackle skin skunk program roster trash rumor slush angel flea amazing"
]


@pytest.mark.setup_client(mnemonic=MNEMONIC_SLIP39_ADVANCED_20, passphrase=False)
def test_2of3_dryrun(client):
    debug = client.debug

    def input_flow():
        yield  # Confirm Dryrun
        debug.press_yes()
        # run recovery flow
        yield from recovery_enter_shares(
            debug, EXTRA_GROUP_SHARE + MNEMONIC_SLIP39_ADVANCED_20, groups=True
        )

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


@pytest.mark.setup_client(mnemonic=MNEMONIC_SLIP39_ADVANCED_20, passphrase=True)
def test_2of3_invalid_seed_dryrun(client):
    debug = client.debug

    def input_flow():
        yield  # Confirm Dryrun
        debug.press_yes()
        # run recovery flow
        yield from recovery_enter_shares(
            debug, INVALID_SHARES_SLIP39_ADVANCED_20, groups=True
        )

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
