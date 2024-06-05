from typing import TYPE_CHECKING

import storage.device as storage_device
from trezor.enums import BackupType

if TYPE_CHECKING:
    from typing import Sequence

    from trezor.messages import BackupDevice, Success


async def perform_backup(
    is_repeated_backup: bool,
    group_threshold: int | None = None,
    groups: Sequence[tuple[int, int]] = (),
) -> None:
    from trezor import TR
    from trezor.enums import ButtonRequestType
    from trezor.ui.layouts import confirm_action
    from trezor.utils import ensure

    from apps.common import backup, backup_types, mnemonic

    from .reset_device import backup_seed, backup_slip39_custom, layout

    # Ask the user to confirm backup. The user can still escape here.
    if is_repeated_backup:
        await confirm_action(
            "confirm_repeated_backup",
            TR.recovery__title_unlock_repeated_backup,
            description=TR.recovery__unlock_repeated_backup,
            br_code=ButtonRequestType.ProtectCall,
            verb=TR.recovery__unlock_repeated_backup_verb,
        )

    mnemonic_secret = mnemonic.get_secret()
    ensure(mnemonic_secret is not None)  # checked at run-time
    assert mnemonic_secret is not None  # checked at type-check time
    backup_type = mnemonic.get_type()

    # upgrade Single to Basic if necessary
    if is_repeated_backup and backup_type == BackupType.Slip39_Single_Extendable:
        # TODO upgrade to Advanced if appropriate
        backup_type = BackupType.Slip39_Basic_Extendable
        storage_device.set_backup_type(backup_type)

    # set unfinished flag -- if the process gets interrupted, the unfinished flag stays
    if not is_repeated_backup:
        storage_device.set_unfinished_backup(True)

    # Deactivate repeated backup, set backed up flag, before showing anything to the
    # user. If anything bad happens from now on, the backup counts as "already done".
    backup.deactivate_repeated_backup()
    storage_device.set_backed_up()

    if group_threshold is not None:
        # Parameters provided from host side.
        assert backup_types.is_slip39_backup_type(backup_type)
        extendable = backup_types.is_extendable_backup_type(backup_type)
        # Run the backup process directly.
        await backup_slip39_custom(mnemonic_secret, group_threshold, groups, extendable)
    else:
        # No parameters provided, allow the user to configure them on screen.
        await backup_seed(backup_type, mnemonic_secret)

    # If the backup was successful, clear the unfinished flag and show success.

    # (NOTE that if the user manages to enable repeated backup while unfinished flag is
    # set, the unfinished flag is cleared here. That is the correct thing to do -- the
    # user _has_ finished the backup because they were able to unlock the repeated
    # backup -- and now they finished another one.)
    storage_device.set_unfinished_backup(False)
    await layout.show_backup_success()


async def backup_device(msg: BackupDevice) -> Success:
    from trezor import wire
    from trezor.messages import Success

    from apps.common import backup, mnemonic

    # do this early before we show any UI
    # the homescreen will clear the flag right after its own UI is gone
    repeated_backup_enabled = backup.repeated_backup_enabled()
    is_repeated_backup = repeated_backup_enabled and not storage_device.needs_backup()

    if not storage_device.is_initialized():
        raise wire.NotInitialized("Device is not initialized")
    if not storage_device.needs_backup() and not repeated_backup_enabled:
        raise wire.ProcessError("Seed already backed up")

    group_threshold = msg.group_threshold
    groups = [(g.member_threshold, g.member_count) for g in msg.groups]

    # validate host-side SLIP39 parameters
    if group_threshold is not None:
        if group_threshold < 1:
            raise wire.DataError("group_threshold must be a positive integer")
        if len(groups) < group_threshold:
            raise wire.DataError("Not enough groups provided for group_threshold")
        if mnemonic.is_bip39():
            raise wire.ProcessError("Expected SLIP39 backup")
    elif len(groups) > 0:
        raise wire.DataError("group_threshold is missing")

    await perform_backup(is_repeated_backup, group_threshold, groups)

    return Success(message="Seed successfully backed up")
