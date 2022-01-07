from typing import TYPE_CHECKING

import storage
import storage.device
from trezor import wire
from trezor.messages import Success

from apps.common import mnemonic

from .reset_device import backup_seed, layout

if TYPE_CHECKING:
    from trezor.messages import BackupDevice


async def backup_device(ctx: wire.Context, msg: BackupDevice) -> Success:
    if not storage.device.is_initialized():
        raise wire.NotInitialized("Device is not initialized")
    if not storage.device.needs_backup():
        raise wire.ProcessError("Seed already backed up")

    mnemonic_secret, mnemonic_type = mnemonic.get()
    if mnemonic_secret is None:
        raise RuntimeError

    storage.device.set_unfinished_backup(True)
    storage.device.set_backed_up()

    await backup_seed(ctx, mnemonic_type, mnemonic_secret)

    storage.device.set_unfinished_backup(False)

    await layout.show_backup_success(ctx)

    return Success(message="Seed successfully backed up")
