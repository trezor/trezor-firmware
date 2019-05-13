from trezor import wire
from trezor.messages.Success import Success

from apps.common import mnemonic, storage
from apps.management.reset_device import (
    check_mnemonic,
    show_backup_warning,
    show_mnemonic,
    show_wrong_entry,
)


async def backup_device(ctx, msg):
    if not storage.is_initialized():
        raise wire.ProcessError("Device is not initialized")
    if not storage.needs_backup():
        raise wire.ProcessError("Seed already backed up")

    words = mnemonic.restore()

    # warn user about mnemonic safety
    await show_backup_warning(ctx)

    storage.set_unfinished_backup(True)
    storage.set_backed_up()

    while True:
        # show mnemonic and require confirmation of a random word
        await show_mnemonic(ctx, words)
        if await check_mnemonic(ctx, words):
            break
        await show_wrong_entry(ctx)

    storage.set_unfinished_backup(False)

    return Success(message="Seed successfully backed up")
