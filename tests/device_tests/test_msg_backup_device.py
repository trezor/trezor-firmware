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
from trezorlib.messages import ButtonRequestType as B

from ..common import (
    MNEMONIC12,
    MNEMONIC_SLIP39_BASIC_20_3of6,
    click_through,
    read_and_confirm_mnemonic,
)


@pytest.mark.skip_t1  # TODO we want this for t1 too
@pytest.mark.setup_client(mnemonic=MNEMONIC12)
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
                messages.Success(),
            ]
        )
        device.backup(client)

    assert mnemonic == MNEMONIC12
    client.init_device()
    assert client.features.needs_backup is False


@pytest.mark.skip_t1
@pytest.mark.setup_client(mnemonic=MNEMONIC_SLIP39_BASIC_20_3of6)
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
                messages.Success(),
            ]
        )
        device.backup(client)

    client.init_device()
    assert client.features.needs_backup is False

    expected_ms = shamir.combine_mnemonics(MNEMONIC_SLIP39_BASIC_20_3of6)
    actual_ms = shamir.combine_mnemonics(mnemonics[:3])
    assert expected_ms == actual_ms
