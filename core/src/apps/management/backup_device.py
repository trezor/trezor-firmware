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

    mnemonic_secret, mnemonic_type = mnemonic.get()
    slip39 = mnemonic_type == mnemonic.TYPE_SLIP39

    # warn user about mnemonic safety
    await layout.show_backup_warning(ctx, "Back up your seed", "I understand", slip39)

    storage.set_unfinished_backup(True)
    storage.set_backed_up()

    if slip39:
        await backup_slip39_wallet(ctx, mnemonic_secret)
    else:
        await layout.bip39_show_and_confirm_mnemonic(ctx, mnemonic_secret.decode())

    storage.set_unfinished_backup(False)

    return Success(message="Seed successfully backed up")
