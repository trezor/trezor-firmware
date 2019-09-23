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
import shamir_mnemonic as shamir

from trezorlib import device, messages
from trezorlib.messages import BackupType, ButtonRequestType as B

from ..common import click_through, generate_entropy, read_and_confirm_mnemonic

EXTERNAL_ENTROPY = b"zlutoucky kun upel divoke ody" * 2
OS_URANDOM = mock.Mock(return_value=EXTERNAL_ENTROPY)


@pytest.mark.skip_t1
@pytest.mark.setup_client(uninitialized=True)
def test_skip_backup_msg(client):
    with mock.patch("os.urandom", OS_URANDOM), client:
        device.reset(
            client,
            display_random=False,
            strength=128,
            skip_backup=True,
            passphrase_protection=False,
            pin_protection=False,
            label="test",
            language="english",
            backup_type=BackupType.Slip39_Advanced,
        )

    assert client.features.initialized is True
    assert client.features.needs_backup is True
    assert client.features.unfinished_backup is False
    assert client.features.no_backup is False
    assert client.features.backup_type is BackupType.Slip39_Advanced

    # generate secret locally
    internal_entropy = client.debug.state().reset_entropy
    secret = generate_entropy(128, internal_entropy, EXTERNAL_ENTROPY)

    mnemonics = backup_flow(client)

    client.init_device()
    assert client.features.initialized is True
    assert client.features.needs_backup is False
    assert client.features.unfinished_backup is False
    assert client.features.backup_type is BackupType.Slip39_Advanced

    assert mnemonics is not []

    validate_mnemonics(mnemonics, secret)


@pytest.mark.skip_t1
@pytest.mark.setup_client(uninitialized=True)
def test_skip_backup_manual(client):
    def reset_skip_input_flow():
        yield  # Confirm Recovery
        client.debug.press_yes()

        yield  # Skip Backup
        client.debug.press_no()

        yield  # Confirm skip backup
        client.debug.press_no()

    with mock.patch("os.urandom", OS_URANDOM), client:
        client.set_input_flow(reset_skip_input_flow)
        client.set_expected_responses(
            [
                messages.ButtonRequest(code=B.ResetDevice),
                messages.EntropyRequest(),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.Success(),
                messages.Features(),
            ]
        )
        device.reset(
            client,
            strength=128,
            pin_protection=False,
            passphrase_protection=False,
            backup_type=BackupType.Slip39_Advanced,
        )

    assert client.features.initialized is True
    assert client.features.needs_backup is True
    assert client.features.unfinished_backup is False
    assert client.features.no_backup is False
    assert client.features.backup_type is BackupType.Slip39_Advanced

    # generate secret locally
    internal_entropy = client.debug.state().reset_entropy
    secret = generate_entropy(128, internal_entropy, EXTERNAL_ENTROPY)

    mnemonics = backup_flow(client)

    client.init_device()
    assert client.features.initialized is True
    assert client.features.needs_backup is False
    assert client.features.unfinished_backup is False
    assert client.features.backup_type is BackupType.Slip39_Advanced

    assert mnemonics is not []

    # generate secret locally
    internal_entropy = client.debug.state().reset_entropy
    secret = generate_entropy(128, internal_entropy, EXTERNAL_ENTROPY)

    validate_mnemonics(mnemonics, secret)


def backup_flow(client):
    all_mnemonics = []

    def input_flow():
        # 1. Confirm Reset
        # 2. shares info
        # 3. Set & Confirm number of groups
        # 4. threshold info
        # 5. Set & confirm group threshold value
        # 6-15: for each of 5 groups:
        #   1. Set & Confirm number of shares
        #   2. Set & confirm share threshold value
        # 16. Confirm show seeds
        yield from click_through(client.debug, screens=16, code=B.ResetDevice)

        # show & confirm shares for all groups
        for g in range(5):
            for h in range(5):
                # mnemonic phrases
                btn_code = yield
                assert btn_code == B.ResetDevice
                mnemonic = read_and_confirm_mnemonic(client.debug, words=20)
                all_mnemonics.append(mnemonic)

                # Confirm continue to next share
                btn_code = yield
                assert btn_code == B.Success
                client.debug.press_yes()

        # safety warning
        btn_code = yield
        assert btn_code == B.Success
        client.debug.press_yes()

    with client:
        client.set_expected_responses(
            [
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
            ]
        )
        client.set_input_flow(input_flow)

        device.backup(client)

    return all_mnemonics


def validate_mnemonics(mnemonics, expected_ems):
    # 3of5 shares 3of5 groups
    test_combination = mnemonics[0:3] + mnemonics[5:8] + mnemonics[10:13]
    ms = shamir.combine_mnemonics(test_combination)
    identifier, iteration_exponent, _, _, _ = shamir._decode_mnemonics(test_combination)
    ems = shamir._encrypt(ms, b"", iteration_exponent, identifier)
    assert ems == expected_ems
