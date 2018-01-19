from micropython import const
from trezor import wire, ui
from trezor.ui.container import Container
from trezor.utils import unimport, chunks
from ubinascii import hexlify

if __debug__:
    internal_entropy = None
    current_word = None

@unimport
async def layout_reset_device(ctx, msg):
    from trezor import config
    from trezor.ui.text import Text
    from trezor.crypto import hashlib, random, bip39, random
    from trezor.ui.keyboard import MnemonicKeyboard
    from trezor.messages.EntropyRequest import EntropyRequest
    from trezor.messages.Success import Success
    from trezor.messages import FailureType
    from trezor.messages import ButtonRequestType
    from trezor.messages.wire_types import EntropyAck
    from apps.management.change_pin import request_pin_confirm
    from apps.common.confirm import require_confirm
    from apps.common import storage

    if __debug__:
        global internal_entropy

    if msg.strength not in (128, 192, 256):
        raise wire.FailureError(
            FailureType.ProcessError, 'Invalid strength (has to be 128, 192 or 256 bits)')

    if storage.is_initialized():
        raise wire.FailureError(
            FailureType.UnexpectedMessage, 'Already initialized')

    internal_entropy = random.bytes(32)

    if msg.display_random:
        entropy_lines = chunks(hexlify(internal_entropy).decode(), 16)
        entropy_content = Text('Internal entropy', ui.ICON_RESET, ui.MONO, *entropy_lines)
        await require_confirm(ctx, entropy_content, ButtonRequestType.ResetDevice)

    if msg.pin_protection:
        curpin = ''
        newpin = await request_pin_confirm(ctx)
    else:
        curpin = ''
        newpin = ''

    external_entropy_ack = await ctx.call(EntropyRequest(), EntropyAck)
    ehash = hashlib.sha256()
    ehash.update(internal_entropy)
    ehash.update(external_entropy_ack.entropy)
    entropy = ehash.digest()
    mnemonic = bip39.from_data(entropy[:msg.strength // 8])

    # seed-copy warning
    warning_content = Text('Backup your seed', ui.ICON_NOCOPY, ui.NORMAL,
                           'Never make a digital',
                           'copy of your recovery',
                           'seed and never upload',
                           'it online!')
    await require_confirm(ctx, warning_content, ButtonRequestType.ResetDevice)

    # ask to write down mnemonic
    await show_mnemonic(mnemonic)

    # ask for random number to check correctness
    words = list(enumerate(mnemonic.split()))
    index = random.uniform(len(words))
    word = words[index][1]
    board = MnemonicKeyboard()
    board.prompt = ('Type %s. word' % (index + 1))
    res = await board
    if res != word:
        fail_content = Text('Wrong entry!', ui.ICON_CLEAR, ui.NORMAL,
                            'You have entered',
                            'wrong seed word.',
                            'Please, reconnect',
                            'device and try again.', icon_color=ui.RED)
        # todo redesign dialog to single cancel button with text 'Reconnect' or something else (no icon)
        await require_confirm(ctx, fail_content, ButtonRequestType.ResetDevice)

    if curpin != newpin:
        config.change_pin(curpin, newpin)
    storage.load_settings(label=msg.label,
                          use_passphrase=msg.passphrase_protection)
    storage.load_mnemonic(mnemonic)

    fail_content = Text('Backup is done!', ui.ICON_CONFIRM, ui.NORMAL,
                        'Never make a digital',
                        'copy of your recovery',
                        'seed and never upload',
                        'it online!', icon_color=ui.GREEN)
    # todo redesign dialog to single cancel button with text 'Finish?' or something else (no icon)
    await require_confirm(ctx, fail_content, ButtonRequestType.ResetDevice)

    return Success(message='Initialized')


async def show_mnemonic_by_word(ctx, mnemonic):
    from trezor.ui.text import Text
    from trezor.messages.ButtonRequestType import ConfirmWord
    from apps.common.confirm import confirm

    words = mnemonic.split()

    if __debug__:
        global current_word

    for index, word in enumerate(words):
        if __debug__:
            current_word = word
        await confirm(ctx,
                      Text('Recovery seed setup', ui.ICON_RESET,
                           ui.NORMAL, 'Write down seed word', '',
                           ui.BOLD, '%d. %s' % (index + 1, word)),
                      ConfirmWord, confirm='Next', cancel=None)

    for index, word in enumerate(words):
        if __debug__:
            current_word = word
        await confirm(ctx,
                      Text('Recovery seed setup', ui.ICON_RESET,
                           ui.NORMAL, 'Confirm seed word', '',
                           ui.BOLD, '%d. %s' % (index + 1, word)),
                      ConfirmWord, confirm='Next', cancel=None)


async def show_mnemonic(mnemonic):
    from trezor.ui.scroll import paginate

    first_page = const(0)
    words_per_page = const(4)
    words = list(enumerate(mnemonic.split()))
    pages = list(chunks(words, words_per_page))
    await paginate(show_mnemonic_page, len(pages), first_page, pages)


async def show_mnemonic_page(page, page_count, mnemonic):
    from trezor.ui.button import Button
    from trezor.ui.text import Text
    from trezor.ui.scroll import Scrollpage, animate_swipe

    lines = []
    for pi, (wi, word) in enumerate(mnemonic[page]):
        pos = wi + 1
        lines.append(str('%d. %s' % (pos, word)))
    ui.display.clear()
    scroll_page = Scrollpage(Text('Recovery seed setup', ui.ICON_RESET, ui.MONO, lines), page, page_count)
    scroll_page.render()
    if page + 1 == page_count:
        await Button(
            (0, 240 - 48, 240, 48),
            'Finalize',
            normal_style=ui.BTN_CONFIRM,
            active_style=ui.BTN_CONFIRM_ACTIVE)
        ui.display.clear()
    else:
        await animate_swipe()
