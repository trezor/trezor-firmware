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

from trezorlib import device, messages

from .. import buttons
from ..common import WITH_MOCK_URANDOM
from . import recovery, reset
from .common import go_next

if TYPE_CHECKING:
    from ..device_handler import BackgroundDeviceHandler


pytestmark = [pytest.mark.skip_t1b1]


@pytest.mark.setup_client(uninitialized=True)
@WITH_MOCK_URANDOM
def test_repeated_backup(
    device_handler: "BackgroundDeviceHandler",
):
    features = device_handler.features()
    debug = device_handler.debuglink()

    assert features.initialized is False

    device_handler.run(
        device.reset,
        strength=128,
        backup_type=messages.BackupType.Slip39_Basic,
        pin_protection=False,
    )

    # confirm new wallet
    reset.confirm_new_wallet(debug)

    # confirm back up
    reset.confirm_read(debug)

    # confirm backup warning
    reset.confirm_read(debug, middle_r=True)

    # let's make a 1-of-1 backup to start with...

    # shares=1
    reset.set_selection(debug, buttons.RESET_MINUS, 5 - 1)

    # confirm checklist
    reset.confirm_read(debug)

    # threshold=1
    reset.set_selection(debug, buttons.RESET_PLUS, 0)

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

    # great ... device is initialized, backup done, and we are not in recovery mode!
    assert device_handler.result() == "Initialized"
    features = device_handler.features()
    assert features.backup_type is messages.BackupType.Slip39_Basic
    assert features.initialized is True
    assert features.needs_backup is False
    assert features.no_backup is False
    assert features.recovery_status == messages.RecoveryStatus.NoRecovery

    # run recovery to unlock backup
    device_handler.run(
        device.recover,
        recovery_kind=messages.RecoveryKind.UnlockRepeatedBackup,
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

    # backup is enabled
    go_next(debug)

    assert device_handler.result().message == "Backup unlocked"

    # we are now in recovery mode
    features = device_handler.features()
    assert features.backup_type is messages.BackupType.Slip39_Basic
    assert features.initialized is True
    assert features.needs_backup is False
    assert features.no_backup is False
    assert (
        features.recovery_status
        == messages.RecoveryStatus.InUnlockRepeatedBackupRecovery
    )

    # at this point, the backup is unlocked...

    # ... so let's try to do a 2-of-3 backup

    # confirm checklist
    reset.confirm_read(debug)

    # shares=3
    reset.set_selection(debug, buttons.RESET_MINUS, 5 - 3)

    # confirm checklist
    reset.confirm_read(debug)

    # threshold=2
    reset.set_selection(debug, buttons.RESET_MINUS, 1)

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
    assert features.backup_type is messages.BackupType.Slip39_Basic
    assert features.initialized is True
    assert features.needs_backup is False
    assert features.no_backup is False
    assert features.recovery_status == messages.RecoveryStatus.NoRecovery

    # try to unlock backup again...
    device_handler.run(
        device.recover,
        recovery_kind=messages.RecoveryKind.UnlockRepeatedBackup,
    )

    recovery.confirm_recovery(debug, "recovery__title_unlock_repeated_backup")

    # ... this time with the 2 shares from the *new* backup, which was a 2-of-3!
    recovery.select_number_of_words(debug, num_of_words=20, unlock_repeated_backup=True)
    recovery.enter_shares(
        debug,
        second_backup_2_of_3[-2:],
        "recovery__title_unlock_repeated_backup",
        "recovery__enter_backup",
        "recovery__unlock_repeated_backup",
    )

    assert device_handler.result().message == "Backup unlocked"

    # we are now in recovery mode again!
    features = device_handler.features()
    assert features.backup_type is messages.BackupType.Slip39_Basic
    assert features.initialized is True
    assert features.needs_backup is False
    assert features.no_backup is False
    assert (
        features.recovery_status
        == messages.RecoveryStatus.InUnlockRepeatedBackupRecovery
    )

    # but if we cancel the backup at this point...
    reset.cancel_backup(debug)

    # ...we are out of recovery mode!
    features = device_handler.features()
    assert features.backup_type is messages.BackupType.Slip39_Basic
    assert features.initialized is True
    assert features.needs_backup is False
    assert features.no_backup is False
    assert features.recovery_status == messages.RecoveryStatus.NoRecovery
