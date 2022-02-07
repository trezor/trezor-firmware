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
from shamir_mnemonic import shamir

from trezorlib import device, messages
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.messages import BackupType, ButtonRequestType as B

from ...common import EXTERNAL_ENTROPY, click_through, read_and_confirm_mnemonic


def backup_flow_bip39(client: Client):
    mnemonic = None

    def input_flow():
        nonlocal mnemonic

        # 1. Confirm Reset
        yield from click_through(client.debug, screens=1, code=B.ResetDevice)

        # mnemonic phrases
        mnemonic = yield from read_and_confirm_mnemonic(client.debug)

        # confirm recovery seed check
        br = yield
        assert br.code == B.Success
        client.debug.press_yes()

        # confirm success
        br = yield
        assert br.code == B.Success
        client.debug.press_yes()

    with client:
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
        client.set_input_flow(input_flow)
        device.backup(client)

    return mnemonic.encode()


def backup_flow_slip39_basic(client: Client):
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
            # Phrase screen
            mnemonic = yield from read_and_confirm_mnemonic(client.debug)
            mnemonics.append(mnemonic)
            yield  # Confirm continue to next
            client.debug.press_yes()

        # Confirm backup
        yield
        client.debug.press_yes()

    with client:
        client.set_input_flow(input_flow)
        client.set_expected_responses(
            [messages.ButtonRequest(code=B.ResetDevice)] * 6  # intro screens
            + [
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.Success),
            ]
            * 5  # individual shares
            + [
                messages.ButtonRequest(code=B.Success),
                messages.Success,
                messages.Features,
            ]
        )
        device.backup(client)

    groups = shamir.decode_mnemonics(mnemonics[:3])
    ems = shamir.recover_ems(groups)
    return ems.ciphertext


def backup_flow_slip39_advanced(client: Client):
    mnemonics = []

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
        for _ in range(5):
            for _ in range(5):
                # mnemonic phrases
                mnemonic = yield from read_and_confirm_mnemonic(client.debug)
                mnemonics.append(mnemonic)

                # Confirm continue to next share
                br = yield
                assert br.code == B.Success
                client.debug.press_yes()

        # safety warning
        br = yield
        assert br.code == B.Success
        client.debug.press_yes()

    with client:
        client.set_input_flow(input_flow)
        client.set_expected_responses(
            [messages.ButtonRequest(code=B.ResetDevice)] * 6  # intro screens
            + [
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.ResetDevice),
            ]
            * 5  # group thresholds
            + [
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.Success),
            ]
            * 25  # individual shares
            + [
                messages.ButtonRequest(code=B.Success),
                messages.Success,
                messages.Features,
            ]
        )
        device.backup(client)

    mnemonics = mnemonics[0:3] + mnemonics[5:8] + mnemonics[10:13]
    groups = shamir.decode_mnemonics(mnemonics)
    ems = shamir.recover_ems(groups)
    return ems.ciphertext


VECTORS = [
    (BackupType.Bip39, backup_flow_bip39),
    (BackupType.Slip39_Basic, backup_flow_slip39_basic),
    (BackupType.Slip39_Advanced, backup_flow_slip39_advanced),
]


@pytest.mark.skip_t1
@pytest.mark.parametrize("backup_type, backup_flow", VECTORS)
@pytest.mark.setup_client(uninitialized=True)
def test_skip_backup_msg(client: Client, backup_type, backup_flow):

    os_urandom = mock.Mock(return_value=EXTERNAL_ENTROPY)
    with mock.patch("os.urandom", os_urandom), client:
        device.reset(
            client,
            skip_backup=True,
            passphrase_protection=False,
            pin_protection=False,
            backup_type=backup_type,
        )

    assert client.features.initialized is True
    assert client.features.needs_backup is True
    assert client.features.unfinished_backup is False
    assert client.features.no_backup is False
    assert client.features.backup_type is backup_type

    secret = backup_flow(client)

    client.init_device()
    assert client.features.initialized is True
    assert client.features.needs_backup is False
    assert client.features.unfinished_backup is False
    assert client.features.backup_type is backup_type

    assert secret is not None
    state = client.debug.state()
    assert state.mnemonic_type is backup_type
    assert state.mnemonic_secret == secret


@pytest.mark.skip_t1
@pytest.mark.parametrize("backup_type, backup_flow", VECTORS)
@pytest.mark.setup_client(uninitialized=True)
def test_skip_backup_manual(client: Client, backup_type, backup_flow):
    def reset_skip_input_flow():
        yield  # Confirm Recovery
        client.debug.press_yes()

        yield  # Skip Backup
        client.debug.press_no()

        yield  # Confirm skip backup
        client.debug.press_no()

    os_urandom = mock.Mock(return_value=EXTERNAL_ENTROPY)
    with mock.patch("os.urandom", os_urandom), client:
        client.set_input_flow(reset_skip_input_flow)
        client.set_expected_responses(
            [
                messages.ButtonRequest(code=B.ResetDevice),
                messages.EntropyRequest(),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.Success,
                messages.Features,
            ]
        )
        device.reset(
            client,
            pin_protection=False,
            passphrase_protection=False,
            backup_type=backup_type,
        )

    assert client.features.initialized is True
    assert client.features.needs_backup is True
    assert client.features.unfinished_backup is False
    assert client.features.no_backup is False
    assert client.features.backup_type is backup_type

    secret = backup_flow(client)

    client.init_device()
    assert client.features.initialized is True
    assert client.features.needs_backup is False
    assert client.features.unfinished_backup is False
    assert client.features.backup_type is backup_type

    assert secret is not None
    state = client.debug.state()
    assert state.mnemonic_type is backup_type
    assert state.mnemonic_secret == secret
