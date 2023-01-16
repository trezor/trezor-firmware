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

from ...common import EXTERNAL_ENTROPY
from ...input_flows import (
    InputFlowBip39Backup,
    InputFlowResetSkipBackup,
    InputFlowSlip39AdvancedBackup,
    InputFlowSlip39BasicBackup,
)


def backup_flow_bip39(client: Client) -> bytes:
    with client:
        IF = InputFlowBip39Backup(client)
        client.set_input_flow(IF.get())
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

    assert IF.mnemonic is not None
    return IF.mnemonic.encode()


def backup_flow_slip39_basic(client: Client):
    with client:
        IF = InputFlowSlip39BasicBackup(client, False)
        client.set_input_flow(IF.get())
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

    groups = shamir.decode_mnemonics(IF.mnemonics[:3])
    ems = shamir.recover_ems(groups)
    return ems.ciphertext


def backup_flow_slip39_advanced(client: Client):
    with client:
        IF = InputFlowSlip39AdvancedBackup(client, False)
        client.set_input_flow(IF.get())
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

    mnemonics = IF.mnemonics[0:3] + IF.mnemonics[5:8] + IF.mnemonics[10:13]
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
    os_urandom = mock.Mock(return_value=EXTERNAL_ENTROPY)
    with mock.patch("os.urandom", os_urandom), client:
        IF = InputFlowResetSkipBackup(client)
        client.set_input_flow(IF.get())
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
