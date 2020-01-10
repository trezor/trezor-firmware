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

from unittest import mock

import pytest

from trezorlib import btc, device, messages
from trezorlib.messages import BackupType, ButtonRequestType as B
from trezorlib.tools import parse_path

from ..common import (
    EXTERNAL_ENTROPY,
    click_through,
    read_and_confirm_mnemonic,
    recovery_enter_shares,
)


@pytest.mark.skip_t1
@pytest.mark.skip_ui
@pytest.mark.setup_client(uninitialized=True)
def test_reset_recovery(client):
    mnemonics = reset(client)
    address_before = btc.get_address(client, "Bitcoin", parse_path("44'/0'/0'/0/0"))
    # we're generating 3of5 groups 3of5 shares each
    test_combinations = [
        mnemonics[0:3]  # shares 1-3 from groups 1-3
        + mnemonics[5:8]
        + mnemonics[10:13],
        mnemonics[2:5]  # shares 3-5 from groups 1-3
        + mnemonics[7:10]
        + mnemonics[12:15],
        mnemonics[10:13]  # shares 1-3 from groups 3-5
        + mnemonics[15:18]
        + mnemonics[20:23],
        mnemonics[12:15]  # shares 3-5 from groups 3-5
        + mnemonics[17:20]
        + mnemonics[22:25],
    ]
    for combination in test_combinations:
        device.wipe(client)
        recover(client, combination)
        address_after = btc.get_address(client, "Bitcoin", parse_path("44'/0'/0'/0/0"))
        assert address_before == address_after


def reset(client, strength=128):
    all_mnemonics = []
    # per SLIP-39: strength in bits, rounded up to nearest multiple of 10, plus 70 bits
    # of metadata, split into 10-bit words
    word_count = ((strength + 9) // 10) + 7

    def input_flow():
        # 1. Confirm Reset
        # 2. Backup your seed
        # 3. Confirm warning
        # 4. shares info
        # 5. Set & Confirm number of groups
        # 6. threshold info
        # 7. Set & confirm group threshold value
        # 8-17: for each of 5 groups:
        #   1. Set & Confirm number of shares
        #   2. Set & confirm share threshold value
        # 18. Confirm show seeds
        yield from click_through(client.debug, screens=18, code=B.ResetDevice)

        # show & confirm shares for all groups
        for g in range(5):
            for h in range(5):
                # mnemonic phrases
                btn_code = yield
                assert btn_code == B.ResetDevice
                mnemonic = read_and_confirm_mnemonic(client.debug, words=word_count)
                all_mnemonics.append(mnemonic)

                # Confirm continue to next share
                btn_code = yield
                assert btn_code == B.Success
                client.debug.press_yes()

        # safety warning
        btn_code = yield
        assert btn_code == B.Success
        client.debug.press_yes()

    os_urandom = mock.Mock(return_value=EXTERNAL_ENTROPY)
    with mock.patch("os.urandom", os_urandom), client:
        client.set_expected_responses(
            [
                messages.ButtonRequest(code=B.ResetDevice),
                messages.EntropyRequest(),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.ResetDevice),  # group #1 counts
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.ResetDevice),  # group #2 counts
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.ResetDevice),  # group #3 counts
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.ResetDevice),  # group #4 counts
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.ResetDevice),  # group #5 counts
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.ResetDevice),  # show seeds
                messages.ButtonRequest(code=B.Success),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.Success),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.Success),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.Success),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.Success),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.Success),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.Success),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.Success),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.Success),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.Success),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.Success),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.Success),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.Success),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.Success),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.Success),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.Success),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.Success),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.Success),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.Success),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.Success),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.Success),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.Success),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.Success),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.Success),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.Success),  # show seeds ends here
                messages.ButtonRequest(code=B.Success),
                messages.Success(),
                messages.Features(),
            ]
        )
        client.set_input_flow(input_flow)

        # No PIN, no passphrase, don't display random
        device.reset(
            client,
            display_random=False,
            strength=strength,
            passphrase_protection=False,
            pin_protection=False,
            label="test",
            language="en-US",
            backup_type=BackupType.Slip39_Advanced,
        )

    # Check if device is properly initialized
    assert client.features.initialized is True
    assert client.features.needs_backup is False
    assert client.features.pin_protection is False
    assert client.features.passphrase_protection is False

    return all_mnemonics


def recover(client, shares):
    debug = client.debug

    def input_flow():
        yield  # Confirm Recovery
        debug.press_yes()
        # run recovery flow
        yield from recovery_enter_shares(debug, shares, groups=True)

    with client:
        client.set_input_flow(input_flow)
        ret = device.recover(client, pin_protection=False, label="label")

    # Workflow successfully ended
    assert ret == messages.Success(message="Device recovered")
    assert client.features.pin_protection is False
    assert client.features.passphrase_protection is False
