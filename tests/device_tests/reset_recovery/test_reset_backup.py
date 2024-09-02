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
from shamir_mnemonic import shamir

from trezorlib import device
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.messages import BackupAvailability, BackupType

from ...common import WITH_MOCK_URANDOM
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
        device.backup(client)

    assert IF.mnemonic is not None
    return IF.mnemonic.encode()


def backup_flow_slip39_basic(client: Client):
    with client:
        IF = InputFlowSlip39BasicBackup(client, False)
        client.set_input_flow(IF.get())
        device.backup(client)

    groups = shamir.decode_mnemonics(IF.mnemonics[:3])
    ems = shamir.recover_ems(groups)
    return ems.ciphertext


def backup_flow_slip39_advanced(client: Client):
    with client:
        IF = InputFlowSlip39AdvancedBackup(client, False)
        client.set_input_flow(IF.get())
        device.backup(client)

    mnemonics = IF.mnemonics[0:3] + IF.mnemonics[5:8] + IF.mnemonics[10:13]
    groups = shamir.decode_mnemonics(mnemonics)
    ems = shamir.recover_ems(groups)
    return ems.ciphertext


VECTORS = [
    (BackupType.Bip39, backup_flow_bip39),
    (BackupType.Slip39_Basic_Extendable, backup_flow_slip39_basic),
    (BackupType.Slip39_Advanced_Extendable, backup_flow_slip39_advanced),
]


@pytest.mark.models("core")
@pytest.mark.parametrize("backup_type, backup_flow", VECTORS)
@pytest.mark.setup_client(uninitialized=True)
def test_skip_backup_msg(client: Client, backup_type, backup_flow):
    with WITH_MOCK_URANDOM, client:
        device.reset(
            client,
            skip_backup=True,
            passphrase_protection=False,
            pin_protection=False,
            backup_type=backup_type,
        )

    assert client.features.initialized is True
    assert client.features.backup_availability == BackupAvailability.Required
    assert client.features.unfinished_backup is False
    assert client.features.no_backup is False
    assert client.features.backup_type is backup_type

    secret = backup_flow(client)

    client.init_device()
    assert client.features.initialized is True
    assert client.features.backup_availability == BackupAvailability.NotAvailable
    assert client.features.unfinished_backup is False
    assert client.features.backup_type is backup_type

    assert secret is not None
    state = client.debug.state()
    assert state.mnemonic_type is backup_type
    assert state.mnemonic_secret == secret


@pytest.mark.models("core")
@pytest.mark.parametrize("backup_type, backup_flow", VECTORS)
@pytest.mark.setup_client(uninitialized=True)
def test_skip_backup_manual(client: Client, backup_type: BackupType, backup_flow):
    with WITH_MOCK_URANDOM, client:
        IF = InputFlowResetSkipBackup(client)
        client.set_input_flow(IF.get())
        device.reset(
            client,
            pin_protection=False,
            passphrase_protection=False,
            backup_type=backup_type,
        )

    assert client.features.initialized is True
    assert client.features.backup_availability == BackupAvailability.Required
    assert client.features.unfinished_backup is False
    assert client.features.no_backup is False
    assert client.features.backup_type is backup_type

    secret = backup_flow(client)

    client.init_device()
    assert client.features.initialized is True
    assert client.features.backup_availability == BackupAvailability.NotAvailable
    assert client.features.unfinished_backup is False
    assert client.features.backup_type is backup_type

    assert secret is not None
    state = client.debug.state()
    assert state.mnemonic_type is backup_type
    assert state.mnemonic_secret == secret
