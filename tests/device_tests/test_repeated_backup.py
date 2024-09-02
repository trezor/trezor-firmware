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

from trezorlib import device, messages
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.exceptions import Cancelled, TrezorFailure

from .. import translations as TR
from ..common import (
    MNEMONIC_SLIP39_SINGLE_EXT_20,
    TEST_ADDRESS_N,
    WITH_MOCK_URANDOM,
    MNEMONIC_SLIP39_BASIC_20_3of6,
)
from ..input_flows import InputFlowSlip39BasicBackup, InputFlowSlip39BasicRecoveryDryRun

pytestmark = pytest.mark.models("core")


@pytest.mark.setup_client(needs_backup=True, mnemonic=MNEMONIC_SLIP39_BASIC_20_3of6)
@WITH_MOCK_URANDOM
def test_repeated_backup(client: Client):
    assert client.features.backup_availability == messages.BackupAvailability.Required
    assert client.features.recovery_status == messages.RecoveryStatus.Nothing

    # initial device backup
    mnemonics = []
    with client:
        IF = InputFlowSlip39BasicBackup(client, False)
        client.set_input_flow(IF.get())
        device.backup(client)
        mnemonics = IF.mnemonics

    assert len(mnemonics) == 5

    # cannot backup, since we already just did that!
    assert (
        client.features.backup_availability == messages.BackupAvailability.NotAvailable
    )
    assert client.features.recovery_status == messages.RecoveryStatus.Nothing
    with pytest.raises(TrezorFailure, match=r".*Seed already backed up"):
        device.backup(client)

    # unlock repeated backup by entering 3 of the 5 shares we have got
    with client:
        IF = InputFlowSlip39BasicRecoveryDryRun(
            client, mnemonics[:3], unlock_repeated_backup=True
        )
        client.set_input_flow(IF.get())
        ret = device.recover(client, type=messages.RecoveryType.UnlockRepeatedBackup)
        assert ret == messages.Success(message="Backup unlocked")
        assert (
            client.features.backup_availability == messages.BackupAvailability.Available
        )
        assert client.features.recovery_status == messages.RecoveryStatus.Backup

    # we can now perform another backup
    with client:
        IF = InputFlowSlip39BasicBackup(client, False, repeated=True)
        client.set_input_flow(IF.get())
        device.backup(client)

    # the backup feature is locked again...
    assert (
        client.features.backup_availability == messages.BackupAvailability.NotAvailable
    )
    assert client.features.recovery_status == messages.RecoveryStatus.Nothing
    with pytest.raises(TrezorFailure, match=r".*Seed already backed up"):
        device.backup(client)


@pytest.mark.setup_client(mnemonic=MNEMONIC_SLIP39_SINGLE_EXT_20)
@WITH_MOCK_URANDOM
def test_repeated_backup_upgrade_single(client: Client):
    assert (
        client.features.backup_availability == messages.BackupAvailability.NotAvailable
    )
    assert client.features.recovery_status == messages.RecoveryStatus.Nothing
    assert client.features.backup_type == messages.BackupType.Slip39_Single_Extendable

    # unlock repeated backup by entering the single share
    with client:
        IF = InputFlowSlip39BasicRecoveryDryRun(
            client, MNEMONIC_SLIP39_SINGLE_EXT_20, unlock_repeated_backup=True
        )
        client.set_input_flow(IF.get())
        ret = device.recover(client, type=messages.RecoveryType.UnlockRepeatedBackup)
        assert ret == messages.Success(message="Backup unlocked")
        assert (
            client.features.backup_availability == messages.BackupAvailability.Available
        )
        assert client.features.recovery_status == messages.RecoveryStatus.Backup

    # we can now perform another backup
    with client:
        IF = InputFlowSlip39BasicBackup(client, False, repeated=True)
        client.set_input_flow(IF.get())
        device.backup(client)

    # backup type was upgraded:
    assert client.features.backup_type == messages.BackupType.Slip39_Basic_Extendable
    # the backup feature is locked again...
    assert (
        client.features.backup_availability == messages.BackupAvailability.NotAvailable
    )
    assert client.features.recovery_status == messages.RecoveryStatus.Nothing
    with pytest.raises(TrezorFailure, match=r".*Seed already backed up"):
        device.backup(client)


@pytest.mark.setup_client(needs_backup=True, mnemonic=MNEMONIC_SLIP39_BASIC_20_3of6)
@WITH_MOCK_URANDOM
def test_repeated_backup_cancel(client: Client):
    assert client.features.backup_availability == messages.BackupAvailability.Required
    assert client.features.recovery_status == messages.RecoveryStatus.Nothing

    # initial device backup
    mnemonics = []
    with client:
        IF = InputFlowSlip39BasicBackup(client, False)
        client.set_input_flow(IF.get())
        device.backup(client)
        mnemonics = IF.mnemonics

    assert len(mnemonics) == 5

    # cannot backup, since we already just did that!
    assert (
        client.features.backup_availability == messages.BackupAvailability.NotAvailable
    )
    assert client.features.recovery_status == messages.RecoveryStatus.Nothing
    with pytest.raises(TrezorFailure, match=r".*Seed already backed up"):
        device.backup(client)

    # unlock repeated backup by entering 3 of the 5 shares we have got
    with client:
        IF = InputFlowSlip39BasicRecoveryDryRun(
            client, mnemonics[:3], unlock_repeated_backup=True
        )
        client.set_input_flow(IF.get())
        ret = device.recover(client, type=messages.RecoveryType.UnlockRepeatedBackup)
        assert ret == messages.Success(message="Backup unlocked")
        assert (
            client.features.backup_availability == messages.BackupAvailability.Available
        )
        assert client.features.recovery_status == messages.RecoveryStatus.Backup

    client.debug.wait_layout()

    # send a Cancel message

    with pytest.raises(Cancelled):
        client.call(messages.Cancel())

    client.refresh_features()

    # the backup feature is locked again...
    assert (
        client.features.backup_availability == messages.BackupAvailability.NotAvailable
    )
    assert client.features.recovery_status == messages.RecoveryStatus.Nothing
    with pytest.raises(TrezorFailure, match=r".*Seed already backed up"):
        device.backup(client)


@pytest.mark.setup_client(needs_backup=True, mnemonic=MNEMONIC_SLIP39_BASIC_20_3of6)
@WITH_MOCK_URANDOM
def test_repeated_backup_send_disallowed_message(client: Client):
    assert client.features.backup_availability == messages.BackupAvailability.Required
    assert client.features.recovery_status == messages.RecoveryStatus.Nothing

    # initial device backup
    mnemonics = []
    with client:
        IF = InputFlowSlip39BasicBackup(client, False)
        client.set_input_flow(IF.get())
        device.backup(client)
        mnemonics = IF.mnemonics

    assert len(mnemonics) == 5

    # cannot backup, since we already just did that!
    assert (
        client.features.backup_availability == messages.BackupAvailability.NotAvailable
    )
    assert client.features.recovery_status == messages.RecoveryStatus.Nothing
    with pytest.raises(TrezorFailure, match=r".*Seed already backed up"):
        device.backup(client)

    # unlock repeated backup by entering 3 of the 5 shares we have got
    with client:
        IF = InputFlowSlip39BasicRecoveryDryRun(
            client, mnemonics[:3], unlock_repeated_backup=True
        )
        client.set_input_flow(IF.get())
        ret = device.recover(client, type=messages.RecoveryType.UnlockRepeatedBackup)
        assert ret == messages.Success(message="Backup unlocked")
        assert (
            client.features.backup_availability == messages.BackupAvailability.Available
        )
        assert client.features.recovery_status == messages.RecoveryStatus.Backup

    client.debug.wait_layout()

    # send a GetAddress message

    resp = client.call_raw(
        messages.GetAddress(
            coin_name="Testnet",
            address_n=TEST_ADDRESS_N,
            show_display=True,
            script_type=messages.InputScriptType.SPENDADDRESS,
        )
    )
    assert isinstance(resp, messages.Failure)
    assert "not allowed" in resp.message

    assert client.features.backup_availability == messages.BackupAvailability.Available
    assert client.features.recovery_status == messages.RecoveryStatus.Backup

    # we are still on the confirmation screen!
    TR.assert_in(
        client.debug.read_layout().text_content(), "recovery__unlock_repeated_backup"
    )
