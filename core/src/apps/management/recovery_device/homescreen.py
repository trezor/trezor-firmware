from trezor import crypto, wire
from trezor.crypto.hashlib import sha256
from trezor.messages.Success import Success
from trezor.utils import consteq

from apps.common import mnemonic, storage
from apps.common.layout import show_success
from apps.common.storage import device
from apps.homescreen.homescreen import homescreen
from apps.management.recovery_device import layout

if False:
    from typing import Union


async def recovery_homescreen(single_run=False) -> None:
    ctx = wire.DummyContext()

    if not device.is_recovery_in_progress():
        raise RuntimeError("Recovery is not in progress!")

    dry_run = device.is_recovery_dry_run()
    word_count = device.get_word_count()
    if not word_count:
        word_count = await _request_word_count(ctx, dry_run)

    mnemonic_module = mnemonic.module_from_word_count(word_count)

    if dry_run:
        await _dry_run_precheck(ctx, word_count, single_run)

    secret = await _request_words(ctx, word_count, mnemonic_module)

    if dry_run:
        result = _dry_run(secret)
        await layout.show_dry_run_result(ctx, result)
        return await _dry_run_result(ctx, result, single_run)

    else:
        mnemonic_module.store(secret, needs_backup=False, no_backup=False)
        await show_success(ctx, ("You have successfully", "recovered your wallet."))

    storage.device.end_recovery_progress()
    if single_run:
        return Success(message="Device recovered")
    await homescreen()


def _dry_run(secret: bytes) -> bool:
    digest_input = sha256(secret).digest()
    stored, _ = mnemonic.get()
    digest_stored = sha256(stored).digest()
    if consteq(digest_stored, digest_input):
        return True
    return False


async def _dry_run_precheck(ctx: wire.Context, word_count: int, single_run: bool):
    _, module_stored = mnemonic.get()
    module_suggested = mnemonic.module_from_word_count(word_count)
    if module_stored != module_suggested:
        await layout.show_dry_run_different_type(ctx)
        return await _dry_run_result(ctx, False, single_run)


async def _dry_run_result(ctx: wire.Context, result: bool, single_run: bool):
    storage.device.end_recovery_progress()
    if single_run:
        if result:
            return Success("The seed is valid and matches the one in the device")
        else:
            raise wire.ProcessError("The seed does not match the one in the device")
    await homescreen()
    raise RuntimeError("Recovery process should not continue after it ended")


async def _request_words(
    ctx: wire.Context,
    word_count: int,
    mnemonic_module: Union[mnemonic.bip39, mnemonic.slip39],
):
    await _first_share_screen(ctx, word_count, mnemonic_module)

    secret = None
    while secret is None:
        # ask for mnemonic words one by one
        words = await layout.request_mnemonic(
            ctx, word_count, mnemonic_module == mnemonic.slip39
        )
        try:
            secret = mnemonic_module.process_single(words)
        except crypto.slip39.MnemonicError:
            await layout.show_invalid_mnemonic(ctx)
            continue

        if not secret:
            await _next_share_screen(ctx, mnemonic_module)
    return secret


async def _first_share_screen(
    ctx: wire.Context,
    word_count: int,
    mnemonic_module: Union[mnemonic.bip39, mnemonic.slip39],
):

    if mnemonic_module == mnemonic.bip39:
        content = layout.RecoveryHomescreen(
            "Enter recovery seed", "(%d words)" % word_count
        )
        await layout.homescreen_dialog(ctx, content, "Enter seed")
    elif not storage.slip39.get_remaining():
        content = layout.RecoveryHomescreen(
            "Enter any share", "(%d words)" % word_count
        )
        await layout.homescreen_dialog(ctx, content, "Enter share")
    else:
        await _next_share_screen(ctx, mnemonic_module)


async def _next_share_screen(
    ctx: wire.Context, mnemonic_module: Union[mnemonic.bip39, mnemonic.slip39]
):
    if mnemonic_module == mnemonic.bip39:
        raise RuntimeError("BIP-39 should have only a single share")
    else:
        remaining = storage.slip39.get_remaining()
        text = "%d more share" % remaining
        if remaining > 1:
            text += "s"
        content = layout.RecoveryHomescreen(text, "needed to enter")
        await layout.homescreen_dialog(ctx, content, "Enter share")


async def _request_word_count(ctx, dry_run: bool) -> int:
    homepage = layout.RecoveryHomescreen("Select number of words")
    await layout.homescreen_dialog(ctx, homepage, "Select")

    # ask for the number of words
    word_count = await layout.request_word_count(ctx, dry_run)
    device.set_word_count(word_count)
    return word_count
