from trezor import wire
from trezor.messages.Success import Success
from trezor.wire import errors

from apps.common import mnemonic, storage
from apps.management.reset_device import (
    check_mnemonic,
    show_mnemonic,
    show_warning,
    show_wrong_entry,
)


async def backup_device(ctx, msg):
    if not storage.is_initialized():
        raise errors.ProcessError("Device is not initialized")
    if not storage.needs_backup():
        raise errors.ProcessError("Seed already backed up")

    words = mnemonic.restore()

    # warn user about mnemonic safety
    await show_warning(ctx)

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
