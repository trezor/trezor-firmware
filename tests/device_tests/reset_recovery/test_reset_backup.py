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
from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.messages import BackupAvailability, BackupType

from ...common import MOCK_GET_ENTROPY
from ...input_flows import (
    InputFlowBip39Backup,
    InputFlowResetSkipBackup,
    InputFlowSlip39AdvancedBackup,
    InputFlowSlip39BasicBackup,
)


def backup_flow_bip39(session: Session) -> bytes:
    with session.client as client:
        IF = InputFlowBip39Backup(client)
        client.set_input_flow(IF.get())
        device.backup(session)

    assert IF.mnemonic is not None
    return IF.mnemonic.encode()


def backup_flow_slip39_basic(session: Session):
    with session.client as client:
        IF = InputFlowSlip39BasicBackup(client, False)
        client.set_input_flow(IF.get())
        device.backup(session)

    groups = shamir.decode_mnemonics(IF.mnemonics[:3])
    ems = shamir.recover_ems(groups)
    return ems.ciphertext


def backup_flow_slip39_advanced(session: Session):
    with session.client as client:
        IF = InputFlowSlip39AdvancedBackup(client, False)
        client.set_input_flow(IF.get())
        device.backup(session)

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
@pytest.mark.uninitialized_session
def test_skip_backup_msg(session: Session, backup_type, backup_flow):
    assert session.features.initialized is False

    with session.client:
        device.setup(
            session,
            skip_backup=True,
            passphrase_protection=False,
            pin_protection=False,
            backup_type=backup_type,
            entropy_check_count=0,
            _get_entropy=MOCK_GET_ENTROPY,
        )

    assert session.features.initialized is True
    assert session.features.backup_availability == BackupAvailability.Required
    assert session.features.unfinished_backup is False
    assert session.features.no_backup is False
    assert session.features.backup_type is backup_type

    secret = backup_flow(session)

    session = session.client.get_session()
    assert session.features.initialized is True
    assert session.features.backup_availability == BackupAvailability.NotAvailable
    assert session.features.unfinished_backup is False
    assert session.features.backup_type is backup_type

    assert secret is not None
    state = session.client.debug.state()
    assert state.mnemonic_type is backup_type
    assert state.mnemonic_secret == secret


@pytest.mark.models("core")
@pytest.mark.parametrize("backup_type, backup_flow", VECTORS)
@pytest.mark.setup_client(uninitialized=True)
@pytest.mark.uninitialized_session
def test_skip_backup_manual(session: Session, backup_type: BackupType, backup_flow):
    assert session.features.initialized is False

    with session.client as client:
        IF = InputFlowResetSkipBackup(client)
        client.set_input_flow(IF.get())
        device.setup(
            session,
            pin_protection=False,
            passphrase_protection=False,
            backup_type=backup_type,
            entropy_check_count=0,
            _get_entropy=MOCK_GET_ENTROPY,
        )

    assert session.features.initialized is True
    assert session.features.backup_availability == BackupAvailability.Required
    assert session.features.unfinished_backup is False
    assert session.features.no_backup is False
    assert session.features.backup_type is backup_type

    secret = backup_flow(session)

    session = session.client.get_session()
    assert session.features.initialized is True
    assert session.features.backup_availability == BackupAvailability.NotAvailable
    assert session.features.unfinished_backup is False
    assert session.features.backup_type is backup_type

    assert secret is not None
    state = session.client.debug.state()
    assert state.mnemonic_type is backup_type
    assert state.mnemonic_secret == secret
