from trezor import wire
from trezor.messages import BackupType
from trezor.messages.Success import Success

from apps.common import mnemonic, storage
from apps.management.reset_device import (
    backup_bip39,
    backup_slip39_advanced,
    backup_slip39_basic,
    layout,
)


async def backup_device(ctx, msg):
    if not storage.is_initialized():
        raise wire.ProcessError("Device is not initialized")
    if not storage.device.needs_backup():
        raise wire.ProcessError("Seed already backed up")

    mnemonic_secret, mnemonic_type = mnemonic.get()

    storage.device.set_unfinished_backup(True)
    storage.device.set_backed_up()

    if mnemonic_type == BackupType.Slip39_Basic:
        await backup_slip39_basic(ctx, mnemonic_secret)
    elif mnemonic_type == BackupType.Slip39_Advanced:
        await backup_slip39_advanced(ctx, mnemonic_secret)
    else:
        await backup_bip39(ctx, mnemonic_secret)

    storage.device.set_unfinished_backup(False)

    await layout.show_backup_success(ctx)

    return Success(message="Seed successfully backed up")
