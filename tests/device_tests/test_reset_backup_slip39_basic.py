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
import shamir_mnemonic as shamir
from shamir_mnemonic import MnemonicError

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
            backup_type=BackupType.Slip39_Basic,
        )

    assert client.features.initialized is True
    assert client.features.needs_backup is True
    assert client.features.unfinished_backup is False
    assert client.features.no_backup is False
    assert client.features.backup_type is BackupType.Slip39_Basic

    # generate secret locally
    internal_entropy = client.debug.state().reset_entropy
    secret = generate_entropy(128, internal_entropy, EXTERNAL_ENTROPY)

    mnemonics = backup_flow(client)

    client.init_device()
    assert client.features.initialized is True
    assert client.features.needs_backup is False
    assert client.features.unfinished_backup is False
    assert client.features.backup_type is BackupType.Slip39_Basic

    assert mnemonics is not []

    validate_mnemonics(mnemonics, 3, secret)


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
            pin_protection=False,
            passphrase_protection=False,
            backup_type=BackupType.Slip39_Basic,
        )

    assert client.features.initialized is True
    assert client.features.needs_backup is True
    assert client.features.unfinished_backup is False
    assert client.features.no_backup is False
    assert client.features.backup_type is BackupType.Slip39_Basic

    # generate secret locally
    internal_entropy = client.debug.state().reset_entropy
    secret = generate_entropy(128, internal_entropy, EXTERNAL_ENTROPY)

    mnemonics = backup_flow(client)

    client.init_device()
    assert client.features.initialized is True
    assert client.features.needs_backup is False
    assert client.features.unfinished_backup is False
    assert client.features.backup_type is BackupType.Slip39_Basic

    assert mnemonics is not []

    validate_mnemonics(mnemonics, 3, secret)


def backup_flow(client):
    mnemonics = []

    def input_flow():
        # 1. Checklist
        # 2. Number of shares (5)
        # 3. Checklist
        # 4. Threshold (3)
        # 5. Checklist
        # 6. Confirm show seeds
        yield from click_through(client.debug, screens=6, code=B.ResetDevice)

        # Mnemonic phrases
        for _ in range(5):
            yield  # Phrase screen
            mnemonic = read_and_confirm_mnemonic(client.debug, words=20)
            mnemonics.append(mnemonic)
            yield  # Confirm continue to next
            client.debug.press_yes()

        # Confirm backup
        yield
        client.debug.press_yes()

    with client:
        client.set_input_flow(input_flow)
        client.set_expected_responses(
            [
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.ResetDevice),
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
                messages.ButtonRequest(code=B.Success),
                messages.Success(),
            ]
        )
        device.backup(client)

    return mnemonics


def validate_mnemonics(mnemonics, threshold, expected_ems):
    # We expect these combinations to recreate the secret properly
    for test_group in combinations(mnemonics, threshold):
        # TODO: HOTFIX, we should fix this properly by modifying and unifying the python-shamir-mnemonic API
        ms = shamir.combine_mnemonics(test_group)
        identifier, iteration_exponent, _, _, _ = shamir._decode_mnemonics(test_group)
        ems = shamir._encrypt(ms, b"", iteration_exponent, identifier)
        assert ems == expected_ems
    # We expect these combinations to raise MnemonicError
    for test_group in combinations(mnemonics, threshold - 1):
        with pytest.raises(
            MnemonicError, match=r".*Expected {} mnemonics.*".format(threshold)
        ):
            shamir.combine_mnemonics(test_group)
