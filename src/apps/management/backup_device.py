from trezor import ui, wire
from trezor.messages.FailureType import ProcessError
from trezor.messages.Success import Success
from apps.common import storage
from apps.management.reset_device import show_warning, show_mnemonic, check_mnemonic, show_wrong_entry


async def backup_device(ctx, msg):

    if not storage.is_initialized():
        raise wire.FailureError(ProcessError, 'Device is not initialized')

    if not storage.needs_backup():
        raise wire.FailureError(ProcessError, 'Seed already backed up')

    mnemonic = storage.get_mnemonic()

    storage.set_backed_up()

    # warn user about mnemonic safety
    await show_warning(ctx)
    while True:
        # show mnemonic and require confirmation of a random word
        await show_mnemonic(ctx, mnemonic)
        if await check_mnemonic(ctx, mnemonic):
            break
        await show_wrong_entry(ctx)

    return Success(message='Seed successfully backed up')
