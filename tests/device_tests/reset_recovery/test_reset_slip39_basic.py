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

from itertools import combinations
from unittest import mock

import pytest
from shamir_mnemonic import MnemonicError, shamir

from trezorlib import device, messages
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.exceptions import TrezorFailure
from trezorlib.messages import BackupType, ButtonRequestType as B

from ...common import (
    EXTERNAL_ENTROPY,
    click_through,
    generate_entropy,
    read_and_confirm_mnemonic,
    read_and_confirm_mnemonic_tr,
)

pytestmark = [pytest.mark.skip_t1]


def reset_device(client: Client, strength):
    member_threshold = 3
    all_mnemonics = []

    def input_flow_tt():
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

    def input_flow_tr():
        yield  # Confirm Reset
        client.debug.press_yes()
        yield  # Backup your seed
        client.debug.press_yes()
        yield  # Checklist
        client.debug.press_yes()
        yield  # Number of shares info
        client.debug.press_yes()
        yield  # Number of shares (5)
        client.debug.input("5")
        yield  # Checklist
        client.debug.press_yes()
        yield  # Threshold info
        client.debug.press_yes()
        yield  # Threshold (3)
        client.debug.input("3")
        yield  # Checklist
        client.debug.press_yes()
        yield  # Confirm show seeds
        client.debug.press_yes()

        # Mnemonic phrases
        for _ in range(5):
            # Phrase screen
            mnemonic = yield from read_and_confirm_mnemonic_tr(client.debug)
            all_mnemonics.append(mnemonic)

            br = yield  # Confirm continue to next
            assert br.code == B.Success
            client.debug.press_yes()

        br = yield  # Confirm backup
        assert br.code == B.Success
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
        if client.features.model == "T":
            client.set_input_flow(input_flow_tt)
        elif client.features.model == "R":
            client.debug.watch_layout(True)
            client.set_input_flow(input_flow_tr)

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
            show_tutorial=False,
        )

    # generate secret locally
    internal_entropy = client.debug.state().reset_entropy
    secret = generate_entropy(strength, internal_entropy, EXTERNAL_ENTROPY)

    # validate that all combinations will result in the correct master secret
    validate_mnemonics(all_mnemonics, member_threshold, secret)

    # Check if device is properly initialized
    assert client.features.initialized is True
    assert client.features.needs_backup is False
    assert client.features.pin_protection is False
    assert client.features.passphrase_protection is False
    assert client.features.backup_type is BackupType.Slip39_Basic

    # backup attempt fails because backup was done in reset
    with pytest.raises(TrezorFailure, match="ProcessError: Seed already backed up"):
        device.backup(client)


@pytest.mark.setup_client(uninitialized=True)
def test_reset_device_slip39_basic(client: Client):
    reset_device(client, 128)


@pytest.mark.setup_client(uninitialized=True)
def test_reset_device_slip39_basic_256(client: Client):
    reset_device(client, 256)


def validate_mnemonics(mnemonics, threshold, expected_ems):
    # We expect these combinations to recreate the secret properly
    for test_group in combinations(mnemonics, threshold):
        groups = shamir.decode_mnemonics(test_group)
        ems = shamir.recover_ems(groups)
        assert expected_ems == ems.ciphertext
    # We expect these combinations to raise MnemonicError
    for test_group in combinations(mnemonics, threshold - 1):
        with pytest.raises(MnemonicError, match=f".*Expected {threshold} mnemonics.*"):
            shamir.combine_mnemonics(test_group)
