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

from ..common import WITH_MOCK_URANDOM, MNEMONIC_SLIP39_BASIC_20_3of6
from ..input_flows import InputFlowSlip39BasicBackup, InputFlowSlip39BasicRecoveryDryRun


@pytest.mark.setup_client(needs_backup=True, mnemonic=MNEMONIC_SLIP39_BASIC_20_3of6)
@pytest.mark.skip_t1b1
@WITH_MOCK_URANDOM
def test_repeated_backup(client: Client):
    assert client.features.needs_backup is True

    # initial device backup
    mnemonics = []
    with client:
        IF = InputFlowSlip39BasicBackup(client, False)
        client.set_input_flow(IF.get())
        device.backup(client)
        mnemonics = IF.mnemonics

    assert len(mnemonics) == 5

    # cannot backup, since we already just did that!
    with pytest.raises(TrezorFailure, match=r".*Seed already backed up"):
        device.backup(client)

    # unlock repeated backup by entering 3 of the 5 shares we have got
    with client:
        IF = InputFlowSlip39BasicRecoveryDryRun(
            client, mnemonics[:3], unlock_repeated_backup=True
        )
        client.set_input_flow(IF.get())
        ret = device.recover(
            client, recovery_kind=messages.RecoveryKind.UnlockRepeatedBackup
        )
        assert ret == messages.Success(message="Backup unlocked")

    # we can now perform another backup
    with client:
        IF = InputFlowSlip39BasicBackup(client, False)
        client.set_input_flow(IF.get())
        device.backup(client)

    # the backup feature is locked again...
    with pytest.raises(TrezorFailure, match=r".*Seed already backed up"):
        device.backup(client)


@pytest.mark.setup_client(needs_backup=True, mnemonic=MNEMONIC_SLIP39_BASIC_20_3of6)
@pytest.mark.skip_t1b1
@WITH_MOCK_URANDOM
def test_repeated_backup_cancel(client: Client):
    assert client.features.needs_backup is True

    # initial device backup
    mnemonics = []
    with client:
        IF = InputFlowSlip39BasicBackup(client, False)
        client.set_input_flow(IF.get())
        device.backup(client)
        mnemonics = IF.mnemonics

    assert len(mnemonics) == 5

    # cannot backup, since we already just did that!
    with pytest.raises(TrezorFailure, match=r".*Seed already backed up"):
        device.backup(client)

    # unlock repeated backup by entering 3 of the 5 shares we have got
    with client:
        IF = InputFlowSlip39BasicRecoveryDryRun(
            client, mnemonics[:3], unlock_repeated_backup=True
        )
        client.set_input_flow(IF.get())
        ret = device.recover(
            client, recovery_kind=messages.RecoveryKind.UnlockRepeatedBackup
        )
        assert ret == messages.Success(message="Backup unlocked")

    client.debug.wait_layout()

    # send a Cancel message

    with pytest.raises(Cancelled):
        client.call(messages.Cancel())

    # the backup feature is locked again...
    with pytest.raises(TrezorFailure, match=r".*Seed already backed up"):
        device.backup(client)
