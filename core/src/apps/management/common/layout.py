import ubinascii
from micropython import const

from trezor import ui, utils
from trezor.crypto import random
from trezor.messages import ButtonRequestType
from trezor.ui.button import Button, ButtonDefault
from trezor.ui.checklist import Checklist
from trezor.ui.info import InfoConfirm
from trezor.ui.loader import LoadingAnimation
from trezor.ui.scroll import Paginated
from trezor.ui.shamir import NumInput
from trezor.ui.text import Text

from apps.common.confirm import confirm, hold_to_confirm, require_confirm

if __debug__:
    from apps import debug


async def show_reset_device_warning(ctx, use_slip39: bool):
    text = Text("Create new wallet", ui.ICON_RESET, new_lines=False)
    if use_slip39:
        text.bold("Create a new wallet")
        text.br()
        text.bold("with Shamir Backup?")
    else:
        text.bold("Do you want to create")
        text.br()
        text.bold("a new wallet?")
    text.br()
    text.br_half()
    text.normal("By continuing you agree")
    text.br()
    text.normal("to")
    text.bold("https://trezor.io/tos")
    await require_confirm(ctx, text, ButtonRequestType.ResetDevice, major_confirm=True)
    await LoadingAnimation()


async def show_internal_entropy(ctx, entropy: bytes):
    entropy_str = ubinascii.hexlify(entropy).decode()
    lines = utils.chunks(entropy_str, 16)
    text = Text("Internal entropy", ui.ICON_RESET)
    text.mono(*lines)
    await require_confirm(ctx, text, ButtonRequestType.ResetDevice)


async def show_backup_success(ctx):
    text = Text("Backup is done!", ui.ICON_CONFIRM, ui.GREEN)
    text.normal(
        "Never make a digital",
        "copy of your recovery",
        "seed and never upload",
        "it online!",
    )
    await require_confirm(
        ctx, text, ButtonRequestType.ResetDevice, confirm="Finish backup", cancel=None
    )


async def confirm_backup(ctx):
    text = Text("Backup wallet", ui.ICON_RESET, new_lines=False)
    text.bold("New wallet created")
    text.br()
    text.bold("successfully!")
    text.br()
    text.br_half()
    text.normal("You should back up your")
    text.br()
    text.normal("new wallet right now.")
    return await confirm(
        ctx,
        text,
        ButtonRequestType.ResetDevice,
        cancel="Skip",
        confirm="Back up",
        major_confirm=True,
    )


async def confirm_backup_again(ctx):
    text = Text("Backup wallet", ui.ICON_RESET, new_lines=False)
    text.bold("Are you sure you want")
    text.br()
    text.bold("to skip the backup?")
    text.br()
    text.br_half()
    text.normal("You can backup Trezor")
    text.br()
    text.normal("anytime later.")
    return await confirm(
        ctx,
        text,
        ButtonRequestType.ResetDevice,
        cancel="Skip",
        confirm="Backup",
        major_confirm=True,
    )


async def _confirm_share_words(ctx, share_index, share_words):
    numbered = list(enumerate(share_words))

    # check a word from the first half
    first_half = numbered[: len(numbered) // 2]
    if not await _confirm_word(ctx, share_index, first_half):
        return False

    # check a word from the second half
    second_half = numbered[len(numbered) // 2 :]
    if not await _confirm_word(ctx, share_index, second_half):
        return False

    return True


async def _confirm_word(ctx, share_index, numbered_share_words):
    # TODO: duplicated words in the choice list

    # shuffle the numbered seed half, slice off the choices we need
    random.shuffle(numbered_share_words)
    numbered_choices = numbered_share_words[: MnemonicWordSelect.NUM_OF_CHOICES]

    # we always confirm the first (random) word index
    checked_index, checked_word = numbered_choices[0]
    if __debug__:
        debug.reset_word_index = checked_index

    # shuffle again so the confirmed word is not always the first choice
    random.shuffle(numbered_choices)

    # let the user pick a word
    choices = [word for _, word in numbered_choices]
    select = MnemonicWordSelect(choices, share_index, checked_index)
    if __debug__:
        selected_word = await ctx.wait(select, debug.input_signal)
    else:
        selected_word = await ctx.wait(select)

    # confirm it is the correct one
    return selected_word == checked_word


async def _show_confirmation_success(ctx, share_index, num_of_shares=None):
    if share_index is None or num_of_shares is None or share_index == num_of_shares - 1:
        text = Text("Recovery seed", ui.ICON_RESET)
        text.bold("You finished verifying")
        text.bold("your recovery shares.")
    else:
        text = Text("Recovery share #%s" % (share_index + 1), ui.ICON_RESET)
        text.bold("Recovery share #%s" % (share_index + 1))
        text.bold("checked successfully.")
        text.normal("Continue with share #%s." % (share_index + 2))
    return await confirm(
        ctx, text, ButtonRequestType.ResetDevice, cancel=None, confirm="Continue"
    )


async def _show_confirmation_failure(ctx, share_index):
    if share_index is None:
        text = Text("Recovery seed", ui.ICON_WRONG, ui.RED)
    else:
        text = Text("Recovery share #%s" % (share_index + 1), ui.ICON_WRONG, ui.RED)
    text.bold("That is the wrong word.")
    text.bold("Please check again.")
    await require_confirm(
        ctx, text, ButtonRequestType.ResetDevice, confirm="Check again", cancel=None
    )


# BIP39
# ===


async def bip39_show_and_confirm_mnemonic(ctx, mnemonic: str):
    words = mnemonic.split()

    while True:
        # display paginated mnemonic on the screen
        await _bip39_show_mnemonic(ctx, words)

        # make the user confirm 2 words from the mnemonic
        if await _confirm_share_words(ctx, None, words):
            await _show_confirmation_success(ctx, None)
            break  # this share is confirmed, go to next one
        else:
            await _show_confirmation_failure(ctx, None)


async def bip39_show_backup_warning(ctx):
    text = Text("Backup your seed", ui.ICON_NOCOPY)
    text.normal(
        "Never make a digital",
        "copy of your recovery",
        "seed and never upload",
        "it online!",
    )
    await require_confirm(
        ctx, text, ButtonRequestType.ResetDevice, confirm="I understand", cancel=None
    )


async def _bip39_show_mnemonic(ctx, words: list):
    # split mnemonic words into pages
    PER_PAGE = const(4)
    words = list(enumerate(words))
    words = list(utils.chunks(words, PER_PAGE))

    # display the pages, with a confirmation dialog on the last one
    pages = [_get_mnemonic_page(page) for page in words]
    paginated = Paginated(pages)

    if __debug__:

        def export_displayed_words():
            # export currently displayed mnemonic words into debuglink
            debug.reset_current_words = [w for _, w in words[paginated.page]]

        paginated.on_change = export_displayed_words
        export_displayed_words()

    await hold_to_confirm(ctx, paginated, ButtonRequestType.ResetDevice)


def _get_mnemonic_page(words: list):
    text = Text("Recovery seed", ui.ICON_RESET)
    for index, word in words:
        text.mono("%2d. %s" % (index + 1, word))
    return text


# SLIP39
# ===

# TODO: yellow cancel style?
# TODO: loading animation style?
# TODO: smaller font or tighter rows to fit more text in
# TODO: icons in checklist


async def slip39_show_checklist_set_shares(ctx):
    checklist = Checklist("Backup checklist", ui.ICON_RESET)
    checklist.add("Set number of shares")
    checklist.add("Set threshold")
    checklist.add(("Write down and check", "all shares"))
    checklist.select(0)
    return await confirm(
        ctx,
        checklist,
        ButtonRequestType.ResetDevice,
        cancel=None,
        confirm="Continue",
    )


async def slip39_show_checklist_set_threshold(ctx, num_of_shares):
    checklist = Checklist("Backup checklist", ui.ICON_RESET)
    checklist.add("Set number of shares")
    checklist.add("Set the threshold")
    checklist.add(("Write down and check", "all backup shares"))
    checklist.select(1)
    return await confirm(
        ctx,
        checklist,
        ButtonRequestType.ResetDevice,
        cancel=None,
        confirm="Continue",
    )


async def slip39_show_checklist_show_shares(ctx, num_of_shares, threshold):
    checklist = Checklist("Backup checklist", ui.ICON_RESET)
    checklist.add("Set number of shares")
    checklist.add("Set the threshold")
    checklist.add(("Write down and check", "all backup shares"))
    checklist.select(2)
    return await confirm(
        ctx,
        checklist,
        ButtonRequestType.ResetDevice,
        cancel=None,
        confirm="Continue",
    )


async def slip39_prompt_number_of_shares(ctx):
    count = 5
    min_count = 2
    max_count = 16

    while True:
        shares = ShamirNumInput(ShamirNumInput.SET_SHARES, count, min_count, max_count)
        confirmed = await confirm(
            ctx,
            shares,
            ButtonRequestType.ResetDevice,
            cancel="Info",
            confirm="Continue",
            major_confirm=True,
            cancel_style=ButtonDefault,
        )
        count = shares.input.count
        if confirmed:
            break
        else:
            info = InfoConfirm(
                "Each recovery share is "
                "a sequence of 20 "
                "words. Next you will "
                "choose how many "
                "shares you need to "
                "recover your wallet."
            )
            await info

    return count


async def slip39_prompt_threshold(ctx, num_of_shares):
    count = num_of_shares // 2 + 1
    min_count = 2
    max_count = num_of_shares

    while True:
        shares = ShamirNumInput(
            ShamirNumInput.SET_THRESHOLD, count, min_count, max_count
        )
        confirmed = await confirm(
            ctx,
            shares,
            ButtonRequestType.ResetDevice,
            cancel="Info",
            confirm="Continue",
            major_confirm=True,
            cancel_style=ButtonDefault,
        )
        count = shares.input.count
        if confirmed:
            break
        else:
            info = InfoConfirm(
                "The threshold sets the "
                "number of shares "
                "needed to recover your "
                "wallet. Set it to %s and "
                "you will need any %s "
                "of your %s shares." % (count, count, num_of_shares)
            )
            await info

    return count


async def slip39_show_and_confirm_shares(ctx, shares):
    for index, share in enumerate(shares):
        share_words = share.split(" ")
        while True:
            # display paginated share on the screen
            await _slip39_show_share_words(ctx, index, share_words)

            # make the user confirm 2 words from the share
            if await _confirm_share_words(ctx, index, share_words):
                await _show_confirmation_success(ctx, index, len(shares))
                break  # this share is confirmed, go to next one
            else:
                await _show_confirmation_failure(ctx, index)


async def _slip39_show_share_words(ctx, share_index, share_words):
    first, chunks, last = _slip39_split_share_into_pages(share_words)

    if share_index is None:
        header_title = "Recovery seed"
    else:
        header_title = "Recovery share #%s" % (share_index + 1)
    header_icon = ui.ICON_RESET
    pages = []  # ui page components
    shares_words_check = []  # check we display correct data

    # first page
    text = Text(header_title, header_icon)
    text.bold("Write down these")
    text.bold("%s words:" % len(share_words))
    text.br_half()
    for index, word in first:
        text.mono("%s. %s" % (index + 1, word))
        shares_words_check.append(word)
    pages.append(text)

    # middle pages
    for chunk in chunks:
        text = Text(header_title, header_icon)
        for index, word in chunk:
            text.mono("%s. %s" % (index + 1, word))
            shares_words_check.append(word)
        pages.append(text)

    # last page
    text = Text(header_title, header_icon)
    for index, word in last:
        text.mono("%s. %s" % (index + 1, word))
        shares_words_check.append(word)
    text.br_half()
    text.bold("I confirm that I wrote")
    text.bold("down all %s words." % len(share_words))
    pages.append(text)

    # pagination
    paginated = Paginated(pages)

    if __debug__:

        word_pages = [first] + chunks + [last]

        def export_displayed_words():
            # export currently displayed mnemonic words into debuglink
            debug.reset_current_words = word_pages[paginated.page]

        paginated.on_change = export_displayed_words
        export_displayed_words()

    # make sure we display correct data
    utils.ensure(share_words == shares_words_check)

    # confirm the share
    await hold_to_confirm(ctx, paginated)  # TODO: customize the loader here


def _slip39_split_share_into_pages(share_words):
    share = list(enumerate(share_words))  # we need to keep track of the word indices
    first = share[:2]  # two words on the first page
    middle = share[2:-2]
    last = share[-2:]  # two words on the last page
    chunks = utils.chunks(middle, 4)  # 4 words on the middle pages
    return first, list(chunks), last


class ShamirNumInput(ui.Control):
    SET_SHARES = object()
    SET_THRESHOLD = object()

    def __init__(self, step, count, min_count, max_count):
        self.step = step
        self.input = NumInput(count, min_count=min_count, max_count=max_count)
        self.input.on_change = self.on_change
        self.repaint = True

    def dispatch(self, event, x, y):
        self.input.dispatch(event, x, y)
        if event is ui.RENDER:
            self.on_render()

    def on_render(self):
        if self.repaint:
            count = self.input.count

            # render the headline
            if self.step is ShamirNumInput.SET_SHARES:
                header = "Set num. of shares"
            elif self.step is ShamirNumInput.SET_THRESHOLD:
                header = "Set threshold"
            ui.header(header, ui.ICON_RESET, ui.TITLE_GREY, ui.BG, ui.ORANGE_ICON)

            # render the counter
            if self.step is ShamirNumInput.SET_SHARES:
                ui.display.text(
                    12,
                    130,
                    "%s people or locations" % count,
                    ui.BOLD,
                    ui.FG,
                    ui.BG,
                    ui.WIDTH - 12,
                )
                ui.display.text(
                    12, 156, "will each hold one share.", ui.NORMAL, ui.FG, ui.BG
                )
            elif self.step is ShamirNumInput.SET_THRESHOLD:
                ui.display.text(
                    12, 130, "For recovery you need", ui.NORMAL, ui.FG, ui.BG
                )
                ui.display.text(
                    12,
                    156,
                    "any %s of the shares." % count,
                    ui.BOLD,
                    ui.FG,
                    ui.BG,
                    ui.WIDTH - 12,
                )

            self.repaint = False

    def on_change(self, count):
        self.repaint = True


class MnemonicWordSelect(ui.Layout):
    NUM_OF_CHOICES = 3

    def __init__(self, words, share_index, word_index):
        self.words = words
        self.share_index = share_index
        self.word_index = word_index
        self.buttons = []
        for i, word in enumerate(words):
            area = ui.grid(i + 2, n_x=1)
            btn = Button(area, word)
            btn.on_click = self.select(word)
            self.buttons.append(btn)
        if share_index is None:
            self.text = Text("Check seed")
        else:
            self.text = Text("Check share #%s" % (share_index + 1))
        self.text.normal("Select the %s word:" % utils.format_ordinal(word_index + 1))

    def dispatch(self, event, x, y):
        for btn in self.buttons:
            btn.dispatch(event, x, y)
        self.text.dispatch(event, x, y)

    def select(self, word):
        def fn():
            raise ui.Result(word)

        return fn
