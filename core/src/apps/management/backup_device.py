from trezor import wire
from trezor.messages.Success import Success

from apps.common import mnemonic, storage
from apps.management.common import layout
from apps.management.reset_device import backup_slip39_wallet


async def backup_device(ctx, msg):
    if not storage.is_initialized():
        raise wire.ProcessError("Device is not initialized")
    if not storage.device.needs_backup():
        raise wire.ProcessError("Seed already backed up")

    mnemonic_secret, mnemonic_type = mnemonic.get()
    is_slip39 = mnemonic_type == mnemonic.TYPE_SLIP39

    storage.device.set_unfinished_backup(True)
    storage.device.set_backed_up()

    if is_slip39:
        await backup_slip39_wallet(ctx, mnemonic_secret)
    else:
        await layout.bip39_show_and_confirm_mnemonic(ctx, mnemonic_secret.decode())

    storage.device.set_unfinished_backup(False)

    await layout.show_backup_success(ctx)

    return Success(message="Seed successfully backed up")
