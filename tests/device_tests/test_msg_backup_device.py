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
import shamir_mnemonic as shamir

from trezorlib import device, messages
from trezorlib.exceptions import TrezorFailure
from trezorlib.messages import ButtonRequestType as B

from ..common import (
    MNEMONIC12,
    MNEMONIC_SLIP39_ADVANCED_20,
    MNEMONIC_SLIP39_BASIC_20_3of6,
    click_through,
    read_and_confirm_mnemonic,
)


@pytest.mark.skip_t1  # TODO we want this for t1 too
@pytest.mark.setup_client(needs_backup=True, mnemonic=MNEMONIC12)
def test_backup_bip39(client):
    assert client.features.needs_backup is True
    mnemonic = None

    def input_flow():
        nonlocal mnemonic
        yield  # Confirm Backup
        client.debug.press_yes()
        yield  # Mnemonic phrases
        mnemonic = read_and_confirm_mnemonic(client.debug, words=12)
        yield  # Confirm success
        client.debug.press_yes()
        yield  # Backup is done
        client.debug.press_yes()

    with client:
        client.set_input_flow(input_flow)
        client.set_expected_responses(
            [
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.Success),
                messages.ButtonRequest(code=B.Success),
                messages.Success,
                messages.Features,
            ]
        )
        device.backup(client)

    assert mnemonic == MNEMONIC12
    client.init_device()
    assert client.features.initialized is True
    assert client.features.needs_backup is False
    assert client.features.unfinished_backup is False
    assert client.features.no_backup is False
    assert client.features.backup_type is messages.BackupType.Bip39


@pytest.mark.skip_t1
@pytest.mark.setup_client(needs_backup=True, mnemonic=MNEMONIC_SLIP39_BASIC_20_3of6)
def test_backup_slip39_basic(client):
    assert client.features.needs_backup is True
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
                messages.Success,
                messages.Features,
            ]
        )
        device.backup(client)

    client.init_device()
    assert client.features.initialized is True
    assert client.features.needs_backup is False
    assert client.features.unfinished_backup is False
    assert client.features.no_backup is False
    assert client.features.backup_type is messages.BackupType.Slip39_Basic

    expected_ms = shamir.combine_mnemonics(MNEMONIC_SLIP39_BASIC_20_3of6)
    actual_ms = shamir.combine_mnemonics(mnemonics[:3])
    assert expected_ms == actual_ms


@pytest.mark.skip_t1
@pytest.mark.setup_client(needs_backup=True, mnemonic=MNEMONIC_SLIP39_ADVANCED_20)
def test_backup_slip39_advanced(client):
    assert client.features.needs_backup is True
    mnemonics = []

    def input_flow():
        # 1. Checklist
        # 2. Set and confirm group count
        # 3. Checklist
        # 4. Set and confirm group threshold
        # 5. Checklist
        # 6-15: for each of 5 groups:
        #   1. Set & Confirm number of shares
        #   2. Set & confirm share threshold value
        # 16. Confirm show seeds
        yield from click_through(client.debug, screens=16, code=B.ResetDevice)

        # Mnemonic phrases
        for _ in range(5):
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
                messages.Success,
                messages.Features,
            ]
        )
        device.backup(client)

    client.init_device()
    assert client.features.initialized is True
    assert client.features.needs_backup is False
    assert client.features.unfinished_backup is False
    assert client.features.no_backup is False
    assert client.features.backup_type is messages.BackupType.Slip39_Advanced

    expected_ms = shamir.combine_mnemonics(MNEMONIC_SLIP39_ADVANCED_20)
    actual_ms = shamir.combine_mnemonics(
        mnemonics[:3] + mnemonics[5:8] + mnemonics[10:13]
    )
    assert expected_ms == actual_ms


# we only test this with bip39 because the code path is always the same
@pytest.mark.setup_client(no_backup=True)
def test_no_backup_fails(client):
    client.ensure_unlocked()
    assert client.features.initialized is True
    assert client.features.no_backup is True
    assert client.features.needs_backup is False

    # backup attempt should fail because no_backup=True
    with pytest.raises(TrezorFailure, match=r".*Seed already backed up"):
        device.backup(client)


# we only test this with bip39 because the code path is always the same
@pytest.mark.setup_client(needs_backup=True)
def test_interrupt_backup_fails(client):
    client.ensure_unlocked()
    assert client.features.initialized is True
    assert client.features.needs_backup is True
    assert client.features.unfinished_backup is False
    assert client.features.no_backup is False

    # start backup
    client.call_raw(messages.BackupDevice())

    # interupt backup by sending initialize
    client.init_device()

    # check that device state is as expected
    assert client.features.initialized is True
    assert client.features.needs_backup is False
    assert client.features.unfinished_backup is True
    assert client.features.no_backup is False

    # Second attempt at backup should fail
    with pytest.raises(TrezorFailure, match=r".*Seed already backed up"):
        device.backup(client)


# we only test this with bip39 because the code path is always the same
@pytest.mark.setup_client(uninitialized=True)
def test_no_backup_show_entropy_fails(client):
    with pytest.raises(
        TrezorFailure, match=r".*Can't show internal entropy when backup is skipped"
    ):
        device.reset(
            client,
            display_random=True,
            strength=128,
            passphrase_protection=False,
            pin_protection=False,
            label="test",
            language="en-US",
            no_backup=True,
        )
