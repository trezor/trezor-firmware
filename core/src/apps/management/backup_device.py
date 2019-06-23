from trezor import wire
from trezor.messages.Success import Success

from apps.common import mnemonic, storage
from apps.management.common import layout
from apps.management.reset_device import backup_slip39_wallet


async def backup_device(ctx, msg):
    if not storage.is_initialized():
        raise wire.ProcessError("Device is not initialized")
    if not storage.needs_backup():
        raise wire.ProcessError("Seed already backed up")

    # warn user about mnemonic safety
    await layout.bip39_show_backup_warning(ctx)

    storage.set_unfinished_backup(True)
    storage.set_backed_up()

    mnemonic_secret, mnemonic_type = mnemonic.get()
    if mnemonic_type == mnemonic.TYPE_BIP39:
        await layout.bip39_show_and_confirm_mnemonic(ctx, mnemonic_secret.decode())

    elif mnemonic_type == mnemonic.TYPE_SLIP39:
        await backup_slip39_wallet(ctx, mnemonic_secret)

    storage.set_unfinished_backup(False)

    return Success(message="Seed successfully backed up")
