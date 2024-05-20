from typing import TYPE_CHECKING

from trezor.enums import BackupType

if TYPE_CHECKING:
    from trezor.messages import BackupDevice, Success


BAK_T_BIP39 = BackupType.Bip39  # global_import_cache


async def backup_device(msg: BackupDevice) -> Success:
    import storage.cache as storage_cache
    import storage.device as storage_device
    from trezor import wire
    from trezor.messages import Success

    from apps.common import backup, backup_types, mnemonic

    from .reset_device import backup_seed, backup_slip39_custom, layout

    # do this early before we show any UI
    # the homescreen will clear the flag right after its own UI is gone
    repeated_backup_unlocked = storage_cache.get_bool(
        storage_cache.APP_RECOVERY_REPEATED_BACKUP_UNLOCKED
    )

    if not storage_device.is_initialized():
        raise wire.NotInitialized("Device is not initialized")
    if not storage_device.needs_backup() and not repeated_backup_unlocked:
        raise wire.ProcessError("Seed already backed up")

    mnemonic_secret, backup_type = mnemonic.get()
    if mnemonic_secret is None:
        raise RuntimeError

    group_threshold = msg.group_threshold
    groups = [(g.member_threshold, g.member_count) for g in msg.groups]

    if group_threshold is not None:
        if group_threshold < 1:
            raise wire.DataError("group_threshold must be a positive integer")
        if len(groups) < group_threshold:
            raise wire.DataError("Not enough groups provided for group_threshold")
        if backup_type == BAK_T_BIP39:
            raise wire.ProcessError("Expected SLIP39 backup")
    elif len(groups) > 0:
        raise wire.DataError("group_threshold is missing")

    if not repeated_backup_unlocked:
        storage_device.set_unfinished_backup(True)

    backup.disable_repeated_backup()
    storage_device.set_backed_up()

    if group_threshold is not None:
        extendable = backup_types.is_extendable_backup_type(backup_type)
        await backup_slip39_custom(mnemonic_secret, group_threshold, groups, extendable)
    else:
        await backup_seed(backup_type, mnemonic_secret)

    storage_device.set_unfinished_backup(False)

    await layout.show_backup_success()

    return Success(message="Seed successfully backed up")
