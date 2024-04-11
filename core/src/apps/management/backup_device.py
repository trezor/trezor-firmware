from typing import TYPE_CHECKING

from trezor.enums import BackupType

if TYPE_CHECKING:
    from trezor.messages import BackupDevice, Success


BAK_T_BIP39 = BackupType.Bip39  # global_import_cache


async def backup_device(msg: BackupDevice) -> Success:
    import storage.device as storage_device
    from trezor import wire
    from trezor.messages import Success

    from apps.common import mnemonic

    from .reset_device import backup_seed, backup_slip39_custom, layout

    if not storage_device.is_initialized():
        raise wire.NotInitialized("Device is not initialized")
    if not storage_device.needs_backup():
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

    storage_device.set_unfinished_backup(True)
    storage_device.set_backed_up()

    if group_threshold is not None:
        await backup_slip39_custom(mnemonic_secret, group_threshold, groups)
    else:
        await backup_seed(backup_type, mnemonic_secret)

    storage_device.set_unfinished_backup(False)

    await layout.show_backup_success()

    return Success(message="Seed successfully backed up")
