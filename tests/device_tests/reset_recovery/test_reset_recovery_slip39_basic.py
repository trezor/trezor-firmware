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

import itertools
from unittest import mock

import pytest

from trezorlib import btc, device, messages
from trezorlib.messages import BackupType, ButtonRequestType as B
from trezorlib.tools import parse_path

from ...common import click_through, read_and_confirm_mnemonic, recovery_enter_shares

EXTERNAL_ENTROPY = b"zlutoucky kun upel divoke ody" * 2
MOCK_OS_URANDOM = mock.Mock(return_value=EXTERNAL_ENTROPY)


@pytest.mark.skip_t1
@pytest.mark.setup_client(uninitialized=True)
@mock.patch("os.urandom", MOCK_OS_URANDOM)
def test_reset_recovery(client):
    mnemonics = reset(client)
    address_before = btc.get_address(client, "Bitcoin", parse_path("44'/0'/0'/0/0"))

    for share_subset in itertools.combinations(mnemonics, 3):
        device.wipe(client)
        selected_mnemonics = share_subset
        recover(client, selected_mnemonics)
        address_after = btc.get_address(client, "Bitcoin", parse_path("44'/0'/0'/0/0"))
        assert address_before == address_after


def reset(client, strength=128):
    all_mnemonics = []

    def input_flow():
        # 1. Confirm Reset
        # 2. Backup your seed
        # 3. Confirm warning
        # 4. shares info
        # 5. Set & Confirm number of shares
        # 6. threshold info
        # 7. Set & confirm threshold value
        # 8. Confirm show seeds
        yield from click_through(client.debug, screens=8, code=B.ResetDevice)

        # show & confirm shares
        for _ in range(5):
            # mnemonic phrases
            mnemonic = yield from read_and_confirm_mnemonic(client.debug)
            all_mnemonics.append(mnemonic)

            # Confirm continue to next share
            br = yield
            assert br.code == B.Success
            client.debug.press_yes()

        # safety warning
        br = yield
        assert br.code == B.Success
        client.debug.press_yes()

    with client:
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
            ]
            + [
                # individual mnemonic
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.Success),
            ]
            * 5  # number of shares
            + [
                messages.ButtonRequest(code=B.Success),
                messages.Success,
                messages.Features,
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
            backup_type=BackupType.Slip39_Basic,
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
        yield from recovery_enter_shares(debug, shares)

    with client:
        client.set_input_flow(input_flow)
        ret = device.recover(client, pin_protection=False, label="label")

    # Workflow successfully ended
    assert ret == messages.Success(message="Device recovered")
    assert client.features.pin_protection is False
    assert client.features.passphrase_protection is False
