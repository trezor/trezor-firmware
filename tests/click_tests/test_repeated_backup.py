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

from typing import TYPE_CHECKING

import pytest

from trezorlib import device, exceptions, messages

from ..common import MOCK_GET_ENTROPY
from . import recovery, reset
from .common import go_next

if TYPE_CHECKING:
    from ..device_handler import BackgroundDeviceHandler


pytestmark = pytest.mark.models("core")


@pytest.mark.setup_client(uninitialized=True)
def test_repeated_backup(
    device_handler: "BackgroundDeviceHandler",
):
    features = device_handler.features()
    debug = device_handler.debuglink()

    assert features.initialized is False

    device_handler.run(
        device.setup,
        strength=128,
        backup_type=messages.BackupType.Slip39_Basic,
        pin_protection=False,
        passphrase_protection=False,
        entropy_check_count=0,
        _get_entropy=MOCK_GET_ENTROPY,
    )

    # confirm new wallet
    reset.confirm_new_wallet(debug)
    # confirm back up
    reset.confirm_read(debug)
    # confirm backup intro
    reset.confirm_read(debug)

    # let's make a 1-of-1 backup to start with...

    # confirm checklist
    reset.confirm_read(debug)
    # shares=1
    reset.set_selection(debug, 1 - 5)
    # confirm checklist
    reset.confirm_read(debug)
    # threshold=1
    reset.set_selection(debug, 0)
    # confirm checklist
    reset.confirm_read(debug)
    # confirm backup warning
    reset.confirm_read(debug, middle_r=True)
    # read words
    initial_backup_1_of_1 = reset.read_words(debug)
    # confirm words
    reset.confirm_words(debug, initial_backup_1_of_1)
    # confirm share checked
    reset.confirm_read(debug)
    # confirm backup done
    reset.confirm_read(debug)
    # Your backup is done
    go_next(debug)

    # retrieve the result to check that it does not raise a failure
    device_handler.result()
    # great ... device is initialized, backup done, and we are not in recovery mode!
    features = device_handler.features()
    assert features.backup_type is messages.BackupType.Slip39_Basic_Extendable
    assert features.initialized is True
    assert features.backup_availability == messages.BackupAvailability.NotAvailable
    assert features.no_backup is False
    assert features.recovery_status == messages.RecoveryStatus.Nothing

    # run recovery to unlock backup
    device_handler.run(
        device.recover,
        type=messages.RecoveryType.UnlockRepeatedBackup,
    )

    recovery.confirm_recovery(debug, "recovery__title_unlock_repeated_backup")
    recovery.select_number_of_words(debug, num_of_words=20, unlock_repeated_backup=True)
    recovery.enter_seed(
        debug,
        initial_backup_1_of_1,
        True,
        "recovery__enter_backup",
        "recovery__unlock_repeated_backup",
    )

    # check non-exception result
    device_handler.result()

    # we are now in recovery mode
    features = device_handler.features()
    assert features.backup_type is messages.BackupType.Slip39_Basic_Extendable
    assert features.initialized is True
    assert features.backup_availability == messages.BackupAvailability.Available
    assert features.no_backup is False
    assert features.recovery_status == messages.RecoveryStatus.Backup

    # at this point, the backup is unlocked...
    go_next(debug)

    # ... so let's try to do a 2-of-3 backup
    # confirm backup intro
    reset.confirm_read(debug)
    # confirm checklist
    reset.confirm_read(debug)
    # shares=3
    reset.set_selection(debug, 3 - 5)
    # confirm checklist
    reset.confirm_read(debug)
    # threshold=2
    reset.set_selection(debug, 2 - 3)
    # confirm checklist
    reset.confirm_read(debug)
    # confirm backup warning
    reset.confirm_read(debug, middle_r=True)

    second_backup_2_of_3: list[str] = []
    for _ in range(3):
        # read words
        words = reset.read_words(debug, do_htc=False)

        # confirm words
        reset.confirm_words(debug, words)

        # confirm share checked
        reset.confirm_read(debug)

        second_backup_2_of_3.append(" ".join(words))

    # we are not in recovery mode anymore, because we finished the backup process!
    features = device_handler.features()
    assert features.backup_type is messages.BackupType.Slip39_Basic_Extendable
    assert features.initialized is True
    assert features.backup_availability == messages.BackupAvailability.NotAvailable
    assert features.no_backup is False
    assert features.recovery_status == messages.RecoveryStatus.Nothing

    # try to unlock backup again...
    device_handler.run(
        device.recover,
        type=messages.RecoveryType.UnlockRepeatedBackup,
    )

    recovery.confirm_recovery(debug, "recovery__title_unlock_repeated_backup")

    # ... this time with the 2 shares from the *new* backup, which was a 2-of-3!
    recovery.select_number_of_words(debug, num_of_words=20, unlock_repeated_backup=True)
    recovery.enter_shares(
        debug,
        second_backup_2_of_3[-2:],
        "recovery__title_dry_run",
        "recovery__enter_backup",
        "recovery__unlock_repeated_backup",
    )

    # check non-exception result
    device_handler.result()

    # we are now in recovery mode again!
    features = device_handler.features()
    assert features.backup_type is messages.BackupType.Slip39_Basic_Extendable
    assert features.initialized is True
    assert features.backup_availability == messages.BackupAvailability.Available
    assert features.no_backup is False
    assert features.recovery_status == messages.RecoveryStatus.Backup

    # but if we cancel the backup at this point...
    reset.cancel_backup(debug)

    # ...we are out of recovery mode!
    features = device_handler.features()
    assert features.backup_type is messages.BackupType.Slip39_Basic_Extendable
    assert features.initialized is True
    assert features.backup_availability == messages.BackupAvailability.NotAvailable
    assert features.no_backup is False
    assert features.recovery_status == messages.RecoveryStatus.Nothing

    # try to unlock backup yet again...
    device_handler.run(
        device.recover,
        type=messages.RecoveryType.UnlockRepeatedBackup,
    )

    recovery.confirm_recovery(debug, "recovery__title_unlock_repeated_backup")

    # but cancel on the word count selection screen!
    recovery.cancel_select_number_of_words(debug, unlock_repeated_backup=True)

    with pytest.raises(exceptions.Cancelled):
        device_handler.result()

    # ...we are out of recovery mode!
    features = device_handler.features()
    assert features.backup_type is messages.BackupType.Slip39_Basic_Extendable
    assert features.initialized is True
    assert features.backup_availability == messages.BackupAvailability.NotAvailable
    assert features.no_backup is False
    assert features.recovery_status == messages.RecoveryStatus.Nothing
