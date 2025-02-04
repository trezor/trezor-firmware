# This file is part of the Trezor project.
#
# Copyright (C) 2012-2024 SatoshiLabs and contributors
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

from trezorlib import device, exceptions, messages
from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.exceptions import Cancelled, TrezorFailure

from .. import translations as TR
from ..common import (
    MNEMONIC_SLIP39_SINGLE_EXT_20,
    TEST_ADDRESS_N,
    MNEMONIC_SLIP39_BASIC_20_3of6,
)
from ..input_flows import InputFlowSlip39BasicBackup, InputFlowSlip39BasicRecoveryDryRun

pytestmark = pytest.mark.models("core")


@pytest.mark.setup_client(needs_backup=True, mnemonic=MNEMONIC_SLIP39_BASIC_20_3of6)
def test_repeated_backup(session: Session):
    assert session.features.backup_availability == messages.BackupAvailability.Required
    assert session.features.recovery_status == messages.RecoveryStatus.Nothing

    # initial device backup
    mnemonics = []
    with session, session.client as client:
        IF = InputFlowSlip39BasicBackup(client, False)
        client.set_input_flow(IF.get())
        device.backup(session)
        mnemonics = IF.mnemonics

    assert len(mnemonics) == 5

    # cannot backup, since we already just did that!
    assert (
        session.features.backup_availability == messages.BackupAvailability.NotAvailable
    )
    assert session.features.recovery_status == messages.RecoveryStatus.Nothing
    with pytest.raises(TrezorFailure, match=r".*Seed already backed up"):
        device.backup(session)

    # unlock repeated backup by entering 3 of the 5 shares we have got
    with session, session.client as client:
        IF = InputFlowSlip39BasicRecoveryDryRun(
            client, mnemonics[:3], unlock_repeated_backup=True
        )
        client.set_input_flow(IF.get())
        device.recover(session, type=messages.RecoveryType.UnlockRepeatedBackup)
        assert (
            session.features.backup_availability
            == messages.BackupAvailability.Available
        )
        assert session.features.recovery_status == messages.RecoveryStatus.Backup

    # we can now perform another backup
    with session, session.client as client:
        IF = InputFlowSlip39BasicBackup(client, False, repeated=True)
        client.set_input_flow(IF.get())
        device.backup(session)

    # the backup feature is locked again...
    assert (
        session.features.backup_availability == messages.BackupAvailability.NotAvailable
    )
    assert session.features.recovery_status == messages.RecoveryStatus.Nothing
    with pytest.raises(TrezorFailure, match=r".*Seed already backed up"):
        device.backup(session)


@pytest.mark.setup_client(mnemonic=MNEMONIC_SLIP39_SINGLE_EXT_20)
def test_repeated_backup_upgrade_single(session: Session):
    assert (
        session.features.backup_availability == messages.BackupAvailability.NotAvailable
    )
    assert session.features.recovery_status == messages.RecoveryStatus.Nothing
    assert session.features.backup_type == messages.BackupType.Slip39_Single_Extendable

    # unlock repeated backup by entering the single share
    with session, session.client as client:
        IF = InputFlowSlip39BasicRecoveryDryRun(
            client, MNEMONIC_SLIP39_SINGLE_EXT_20, unlock_repeated_backup=True
        )
        client.set_input_flow(IF.get())
        device.recover(session, type=messages.RecoveryType.UnlockRepeatedBackup)
        assert (
            session.features.backup_availability
            == messages.BackupAvailability.Available
        )
        assert session.features.recovery_status == messages.RecoveryStatus.Backup

    # we can now perform another backup
    with session, session.client as client:
        IF = InputFlowSlip39BasicBackup(client, False, repeated=True)
        client.set_input_flow(IF.get())
        device.backup(session)

    # backup type was upgraded:
    assert session.features.backup_type == messages.BackupType.Slip39_Basic_Extendable
    # the backup feature is locked again...
    assert (
        session.features.backup_availability == messages.BackupAvailability.NotAvailable
    )
    assert session.features.recovery_status == messages.RecoveryStatus.Nothing
    with pytest.raises(TrezorFailure, match=r".*Seed already backed up"):
        device.backup(session)


@pytest.mark.setup_client(needs_backup=True, mnemonic=MNEMONIC_SLIP39_BASIC_20_3of6)
def test_repeated_backup_cancel(session: Session):
    assert session.features.backup_availability == messages.BackupAvailability.Required
    assert session.features.recovery_status == messages.RecoveryStatus.Nothing

    # initial device backup
    mnemonics = []
    with session, session.client as client:
        IF = InputFlowSlip39BasicBackup(client, False)
        client.set_input_flow(IF.get())
        device.backup(session)
        mnemonics = IF.mnemonics

    assert len(mnemonics) == 5

    # cannot backup, since we already just did that!
    assert (
        session.features.backup_availability == messages.BackupAvailability.NotAvailable
    )
    assert session.features.recovery_status == messages.RecoveryStatus.Nothing
    with pytest.raises(TrezorFailure, match=r".*Seed already backed up"):
        device.backup(session)

    # unlock repeated backup by entering 3 of the 5 shares we have got
    with session, session.client as client:
        IF = InputFlowSlip39BasicRecoveryDryRun(
            client, mnemonics[:3], unlock_repeated_backup=True
        )
        client.set_input_flow(IF.get())
        device.recover(session, type=messages.RecoveryType.UnlockRepeatedBackup)
        assert (
            session.features.backup_availability
            == messages.BackupAvailability.Available
        )
        assert session.features.recovery_status == messages.RecoveryStatus.Backup

    layout = session.client.debug.read_layout()
    assert TR.recovery__unlock_repeated_backup in layout.text_content()

    # send a Cancel message

    with pytest.raises(Cancelled):
        session.call(messages.Cancel())

    session.refresh_features()

    # the backup feature is locked again...
    assert (
        session.features.backup_availability == messages.BackupAvailability.NotAvailable
    )
    assert session.features.recovery_status == messages.RecoveryStatus.Nothing
    with pytest.raises(TrezorFailure, match=r".*Seed already backed up"):
        device.backup(session)


@pytest.mark.setup_client(needs_backup=True, mnemonic=MNEMONIC_SLIP39_BASIC_20_3of6)
def test_repeated_backup_send_disallowed_message(session: Session):
    assert session.features.backup_availability == messages.BackupAvailability.Required
    assert session.features.recovery_status == messages.RecoveryStatus.Nothing

    # initial device backup
    mnemonics = []
    with session, session.client as client:
        IF = InputFlowSlip39BasicBackup(client, False)
        client.set_input_flow(IF.get())
        device.backup(session)
        mnemonics = IF.mnemonics

    assert len(mnemonics) == 5

    # cannot backup, since we already just did that!
    assert (
        session.features.backup_availability == messages.BackupAvailability.NotAvailable
    )
    assert session.features.recovery_status == messages.RecoveryStatus.Nothing
    with pytest.raises(TrezorFailure, match=r".*Seed already backed up"):
        device.backup(session)

    # unlock repeated backup by entering 3 of the 5 shares we have got
    with session, session.client as client:
        IF = InputFlowSlip39BasicRecoveryDryRun(
            client, mnemonics[:3], unlock_repeated_backup=True
        )
        client.set_input_flow(IF.get())
        device.recover(session, type=messages.RecoveryType.UnlockRepeatedBackup)
        assert (
            session.features.backup_availability
            == messages.BackupAvailability.Available
        )
        assert session.features.recovery_status == messages.RecoveryStatus.Backup

    layout = session.client.debug.read_layout()
    assert TR.recovery__unlock_repeated_backup in layout.text_content()

    # send a GetAddress message

    resp = session.call_raw(
        messages.GetAddress(
            coin_name="Testnet",
            address_n=TEST_ADDRESS_N,
            show_display=True,
            script_type=messages.InputScriptType.SPENDADDRESS,
        )
    )
    assert isinstance(resp, messages.Failure)
    assert "not allowed" in resp.message

    assert session.features.backup_availability == messages.BackupAvailability.Available
    assert session.features.recovery_status == messages.RecoveryStatus.Backup

    # we are still on the confirmation screen!
    assert (
        TR.recovery__unlock_repeated_backup
        in session.client.debug.read_layout().text_content()
    )
    with pytest.raises(exceptions.Cancelled):
        session.call(messages.Cancel())
