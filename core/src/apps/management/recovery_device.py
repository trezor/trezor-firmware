from trezor import config, ui, wire
from trezor.messages import ButtonRequestType
from trezor.messages.ButtonRequest import ButtonRequest
from trezor.messages.MessageType import ButtonAck
from trezor.messages.Success import Success
from trezor.pin import pin_to_int
from trezor.ui.info import InfoConfirm
from trezor.ui.mnemonic_bip39 import Bip39Keyboard
from trezor.ui.mnemonic_slip39 import Slip39Keyboard
from trezor.ui.text import Text
from trezor.ui.word_select import WordSelector
from trezor.utils import format_ordinal
from trezor.crypto import slip39

from apps.common import mnemonic, storage
from apps.common.confirm import require_confirm
from apps.homescreen.homescreen import display_homescreen
from apps.management.change_pin import request_pin_ack, request_pin_confirm

if __debug__:
    from apps.debug import confirm_signal, input_signal


async def recovery_device(ctx, msg):
    """
    Recover BIP39/SLIP39 seed into empty device.

    1. Ask for the number of words in recovered seed.
    2. Let user type in the mnemonic words one by one.
    3. Optionally check the seed validity.
    4. Optionally ask for the PIN, with confirmation.
    5. Save into storage.
    """
    if not msg.dry_run and storage.is_initialized():
        raise wire.UnexpectedMessage("Already initialized")

    if not storage.is_slip39_in_progress():
        if not msg.dry_run:
            title = "Wallet recovery"
            text = Text(title, ui.ICON_RECOVERY)
            text.normal("Do you really want to", "recover the wallet?", "")
        else:
            title = "Simulated recovery"
            text = Text(title, ui.ICON_RECOVERY)
            text.normal("Do you really want to", "check the recovery", "seed?")
        await require_confirm(ctx, text, code=ButtonRequestType.ProtectCall)

        if msg.dry_run:
            if config.has_pin():
                curpin = await request_pin_ack(ctx, "Enter PIN", config.get_pin_rem())
            else:
                curpin = ""
            if not config.check_pin(pin_to_int(curpin)):
                raise wire.PinInvalid("PIN invalid")

        # ask for the number of words
        wordcount = await request_wordcount(ctx, title)
        mnemonic_module = mnemonic.module_from_words_count(wordcount)
    else:
        wordcount = storage.get_slip39_words_count()
        mnemonic_module = mnemonic.slip39

    if mnemonic_module == mnemonic.slip39:
        # show a note about the keyboard
        await show_keyboard_info(ctx)

    if msg.dry_run:
        dry_run_mnemonics = []
        dry_run_mnemonic_count = None

    secret = None
    while secret is None:
        # ask for mnemonic words one by one
        words = await request_mnemonic(
            ctx, wordcount, mnemonic_module == mnemonic.slip39
        )
        try:
            if msg.dry_run:
                if dry_run_mnemonic_count is None:
                    dry_run_mnemonic_count = mnemonic_module.get_mnemonic_count(words)
                dry_run_mnemonics.append(words)
            else:
                secret = mnemonic_module.process_single(words)
        except slip39.MnemonicError as e:
            raise wire.ProcessError("Mnemonic is not valid: " + str(e))
        if msg.dry_run:
            remaining = dry_run_mnemonic_count - len(dry_run_mnemonics)
            if remaining == 0:
                secret = mnemonic_module.process_all(dry_run_mnemonics)
        else:
            remaining = storage.get_slip39_remaining()
        # show a number of remaining mnemonics for SLIP39
        if secret is None and mnemonic_module == mnemonic.slip39:
            await show_remaining_slip39_mnemonics(ctx, title, remaining)

    # check mnemonic validity
    # it is checked automatically in SLIP-39
    if mnemonic_module == mnemonic.bip39 and (msg.enforce_wordlist or msg.dry_run):
        if not mnemonic_module.check(secret):
            raise wire.ProcessError("Mnemonic is not valid")

    # ask for pin repeatedly
    if msg.pin_protection:
        newpin = await request_pin_confirm(ctx, allow_cancel=False)
    else:
        newpin = ""

    # dry run
    if msg.dry_run:
        return mnemonic.dry_run(secret)

    # save into storage
    if msg.pin_protection:
        config.change_pin(pin_to_int(""), pin_to_int(newpin))
    storage.set_u2f_counter(msg.u2f_counter)
    storage.load_settings(label=msg.label, use_passphrase=msg.passphrase_protection)
    mnemonic_module.store(secret=secret, needs_backup=False, no_backup=False)

    await show_success(ctx)
    display_homescreen()

    return Success(message="Device recovered")


async def request_wordcount(ctx, title: str) -> int:
    await ctx.call(ButtonRequest(code=ButtonRequestType.MnemonicWordCount), ButtonAck)

    text = Text(title, ui.ICON_RECOVERY)
    text.normal("Number of words?")

    if __debug__:
        count = await ctx.wait(WordSelector(text), input_signal)
        count = int(count)  # if input_signal was triggered, count is a string
    else:
        count = await ctx.wait(WordSelector(text))

    return count


async def request_mnemonic(ctx, count: int, slip39: bool) -> str:
    await ctx.call(ButtonRequest(code=ButtonRequestType.MnemonicInput), ButtonAck)

    words = []
    for i in range(count):
        if slip39:
            keyboard = Slip39Keyboard("Type the %s word:" % format_ordinal(i + 1))
        else:
            keyboard = Bip39Keyboard("Type the %s word:" % format_ordinal(i + 1))
        if __debug__:
            word = await ctx.wait(keyboard, input_signal)
        else:
            word = await ctx.wait(keyboard)
        words.append(word)

    return " ".join(words)


async def show_keyboard_info(ctx):
    await ctx.call(ButtonRequest(code=ButtonRequestType.Other), ButtonAck)

    info = InfoConfirm(
        "One more thing. "
        "You can type the letters "
        "the old-fashioned way "
        "one by one or use our "
        "T9 keyboard and press "
        "buttons only once."
    )
    if __debug__:
        await ctx.wait(info, confirm_signal)
    else:
        await ctx.wait(info)


async def show_success(ctx):
    text = Text("Recovery success", ui.ICON_RECOVERY)
    text.normal("You have successfully")
    text.normal("recovered your wallet.")
    await require_confirm(
        ctx, text, ButtonRequestType.ProtectCall, cancel=None, confirm="Continue"
    )


async def show_remaining_slip39_mnemonics(ctx, title, remaining: int):
    text = Text(title, ui.ICON_RECOVERY)
    text.bold("Good job!")
    text.normal("Enter %s more recovery " % remaining)
    if remaining > 1:
        text.normal("shares.")
    else:
        text.normal("share.")
    await require_confirm(
        ctx, text, ButtonRequestType.ProtectCall, cancel=None, confirm="Continue"
    )
