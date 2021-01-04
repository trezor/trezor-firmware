import ubinascii

from trezor import ui, utils
from trezor.crypto import random
from trezor.messages import BackupType, ButtonRequestType
from trezor.ui.components.tt.button import Button, ButtonDefault
from trezor.ui.components.tt.checklist import Checklist
from trezor.ui.components.tt.info import InfoConfirm
from trezor.ui.components.tt.num_input import NumInput
from trezor.ui.components.tt.scroll import Paginated
from trezor.ui.components.tt.text import Text
from trezor.ui.layouts import require, show_success

from apps.common.confirm import confirm, require_confirm, require_hold_to_confirm

if False:
    from trezor import loop
    from typing import List, Tuple

if __debug__:
    from apps import debug


async def show_internal_entropy(ctx, entropy: bytes):
    entropy_str = ubinascii.hexlify(entropy).decode()
    lines = utils.chunks(entropy_str, 16)
    text = Text("Internal entropy", ui.ICON_RESET)
    text.mono(*lines)
    await require_confirm(ctx, text, ButtonRequestType.ResetDevice)


async def _show_share_words(ctx, share_words, share_index=None, group_index=None):
    first, chunks, last = _split_share_into_pages(share_words)

    if share_index is None:
        header_title = "Recovery seed"
    elif group_index is None:
        header_title = "Recovery share #%s" % (share_index + 1)
    else:
        header_title = "Group %s - Share %s" % ((group_index + 1), (share_index + 1))
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
    text.bold("I wrote down all %s" % len(share_words))
    text.bold("words in order.")
    pages.append(text)

    # pagination
    paginated = Paginated(pages)

    if __debug__:

        word_pages = [first] + chunks + [last]

        def export_displayed_words():
            # export currently displayed mnemonic words into debuglink
            words = [w for _, w in word_pages[paginated.page]]
            debug.reset_current_words.publish(words)

        paginated.on_change = export_displayed_words
        export_displayed_words()

    # make sure we display correct data
    utils.ensure(share_words == shares_words_check)

    # confirm the share
    await require_hold_to_confirm(
        ctx, paginated, ButtonRequestType.ResetDevice, cancel=False
    )


def _split_share_into_pages(share_words):
    share = list(enumerate(share_words))  # we need to keep track of the word indices
    first = share[:2]  # two words on the first page
    length = len(share_words)
    if length == 12 or length == 20 or length == 24:
        middle = share[2:-2]
        last = share[-2:]  # two words on the last page
    elif length == 33 or length == 18:
        middle = share[2:]
        last = []  # no words at the last page, because it does not add up
    else:
        # Invalid number of shares. SLIP-39 allows 20 or 33 words, BIP-39 12 or 24
        raise RuntimeError

    chunks = utils.chunks(middle, 4)  # 4 words on the middle pages
    return first, list(chunks), last


async def _confirm_share_words(ctx, share_index, share_words, group_index=None):
    # divide list into thirds, rounding up, so that chunking by `third` always yields
    # three parts (the last one might be shorter)
    third = (len(share_words) + 2) // 3

    offset = 0
    count = len(share_words)
    for part in utils.chunks(share_words, third):
        if not await _confirm_word(ctx, share_index, part, offset, count, group_index):
            return False
        offset += len(part)

    return True


async def _confirm_word(ctx, share_index, share_words, offset, count, group_index=None):
    # remove duplicates
    non_duplicates = list(set(share_words))
    # shuffle list
    random.shuffle(non_duplicates)
    # take top NUM_OF_CHOICES words
    choices = non_duplicates[: MnemonicWordSelect.NUM_OF_CHOICES]
    # select first of them
    checked_word = choices[0]
    # find its index
    checked_index = share_words.index(checked_word) + offset
    # shuffle again so the confirmed word is not always the first choice
    random.shuffle(choices)

    if __debug__:
        debug.reset_word_index.publish(checked_index)

    # let the user pick a word
    select = MnemonicWordSelect(choices, share_index, checked_index, count, group_index)
    selected_word = await ctx.wait(select)
    # confirm it is the correct one
    return selected_word == checked_word


async def _show_confirmation_success(
    ctx, share_index=None, num_of_shares=None, group_index=None
):
    if share_index is None:  # it is a BIP39 backup
        subheader = "You have finished\nverifying your\nrecovery seed."
        text = ""

    elif share_index == num_of_shares - 1:
        if group_index is None:
            subheader = "You have finished\nverifying your\nrecovery shares."
        else:
            subheader = (
                "You have finished\nverifying your\nrecovery shares\nfor group %s."
                % (group_index + 1)
            )
        text = ""

    else:
        if group_index is None:
            subheader = "Recovery share #%s\nchecked successfully." % (share_index + 1)
            text = "Continue with share #%s." % (share_index + 2)
        else:
            subheader = "Group %s - Share %s\nchecked successfully." % (
                (group_index + 1),
                (share_index + 1),
            )
            text = "Continue with the next\nshare."

    return await require(
        show_success(ctx, "success_recovery", text, subheader=subheader)
    )


async def _show_confirmation_failure(ctx, share_index):
    if share_index is None:
        text = Text("Recovery seed", ui.ICON_WRONG, ui.RED)
    else:
        text = Text("Recovery share #%s" % (share_index + 1), ui.ICON_WRONG, ui.RED)
    text.bold("That is the wrong word.")
    text.normal("Please check again.")
    await require_confirm(
        ctx, text, ButtonRequestType.ResetDevice, confirm="Check again", cancel=None
    )


async def show_backup_warning(ctx, slip39=False):
    text = Text("Caution", ui.ICON_NOCOPY)
    if slip39:
        text.normal(
            "Never make a digital",
            "copy of your recovery",
            "shares and never upload",
            "them online!",
        )
    else:
        text.normal(
            "Never make a digital",
            "copy of your recovery",
            "seed and never upload",
            "it online!",
        )
    await require_confirm(
        ctx, text, ButtonRequestType.ResetDevice, "I understand", cancel=None
    )


async def show_backup_success(ctx):
    text = "Use your backup\nwhen you need to\nrecover your wallet."
    await require(
        show_success(ctx, "success_backup", text, subheader="Your backup is done.")
    )


# BIP39
# ===


async def bip39_show_and_confirm_mnemonic(ctx, mnemonic: str):
    # warn user about mnemonic safety
    await show_backup_warning(ctx)

    words = mnemonic.split()

    while True:
        # display paginated mnemonic on the screen
        await _show_share_words(ctx, share_words=words)

        # make the user confirm some words from the mnemonic
        if await _confirm_share_words(ctx, None, words):
            await _show_confirmation_success(ctx)
            break  # this share is confirmed, go to next one
        else:
            await _show_confirmation_failure(ctx, None)


# SLIP39
# ===


async def slip39_show_checklist(ctx, step: int, backup_type: BackupType) -> None:
    checklist = Checklist("Backup checklist", ui.ICON_RESET)
    if backup_type is BackupType.Slip39_Basic:
        checklist.add("Set number of shares")
        checklist.add("Set threshold")
        checklist.add(("Write down and check", "all recovery shares"))
    elif backup_type is BackupType.Slip39_Advanced:
        checklist.add("Set number of groups")
        checklist.add("Set group threshold")
        checklist.add(("Set size and threshold", "for each group"))
    checklist.select(step)

    return await confirm(
        ctx, checklist, ButtonRequestType.ResetDevice, cancel=None, confirm="Continue"
    )


async def slip39_prompt_threshold(ctx, num_of_shares, group_id=None):
    count = num_of_shares // 2 + 1
    # min value of share threshold is 2 unless the number of shares is 1
    # number of shares 1 is possible in advnaced slip39
    min_count = min(2, num_of_shares)
    max_count = num_of_shares

    while True:
        shares = Slip39NumInput(
            Slip39NumInput.SET_THRESHOLD, count, min_count, max_count, group_id
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

        text = "The threshold sets the number of shares "
        if group_id is None:
            text += "needed to recover your wallet. "
            text += "Set it to %s and you will need " % count
            if num_of_shares == 1:
                text += "1 share."
            elif num_of_shares == count:
                text += "all %s of your %s shares." % (count, num_of_shares)
            else:
                text += "any %s of your %s shares." % (count, num_of_shares)
        else:
            text += "needed to form a group. "
            text += "Set it to %s and you will " % count
            if num_of_shares == 1:
                text += "need 1 share "
            elif num_of_shares == count:
                text += "need all %s of %s shares " % (count, num_of_shares)
            else:
                text += "need any %s of %s shares " % (count, num_of_shares)
            text += "to form Group %s." % (group_id + 1)
        info = InfoConfirm(text)
        await info

    return count


async def slip39_prompt_number_of_shares(ctx, group_id=None):
    count = 5
    min_count = 1
    max_count = 16

    while True:
        shares = Slip39NumInput(
            Slip39NumInput.SET_SHARES, count, min_count, max_count, group_id
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

        if group_id is None:
            info = InfoConfirm(
                "Each recovery share is a "
                "sequence of 20 words. "
                "Next you will choose "
                "how many shares you "
                "need to recover your "
                "wallet."
            )
        else:
            info = InfoConfirm(
                "Each recovery share is a "
                "sequence of 20 words. "
                "Next you will choose "
                "the threshold number of "
                "shares needed to form "
                "Group %s." % (group_id + 1)
            )
        await info

    return count


async def slip39_basic_show_and_confirm_shares(ctx, shares):
    # warn user about mnemonic safety
    await show_backup_warning(ctx, slip39=True)

    for index, share in enumerate(shares):
        share_words = share.split(" ")
        while True:
            # display paginated share on the screen
            await _show_share_words(ctx, share_words, index)

            # make the user confirm words from the share
            if await _confirm_share_words(ctx, index, share_words):
                await _show_confirmation_success(
                    ctx, share_index=index, num_of_shares=len(shares)
                )
                break  # this share is confirmed, go to next one
            else:
                await _show_confirmation_failure(ctx, index)


async def slip39_advanced_prompt_number_of_groups(ctx):
    count = 5
    min_count = 2
    max_count = 16

    while True:
        shares = Slip39NumInput(Slip39NumInput.SET_GROUPS, count, min_count, max_count)
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

        info = InfoConfirm(
            "Each group has a set "
            "number of shares and "
            "its own threshold. In the "
            "next steps you will set "
            "the numbers of shares "
            "and the thresholds."
        )
        await info

    return count


async def slip39_advanced_prompt_group_threshold(ctx, num_of_groups):
    count = num_of_groups // 2 + 1
    min_count = 1
    max_count = num_of_groups

    while True:
        shares = Slip39NumInput(
            Slip39NumInput.SET_GROUP_THRESHOLD, count, min_count, max_count
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
                "The group threshold "
                "specifies the number of "
                "groups required to "
                "recover your wallet. "
            )
            await info

    return count


async def slip39_advanced_show_and_confirm_shares(ctx, shares):
    # warn user about mnemonic safety
    await show_backup_warning(ctx, slip39=True)

    for group_index, group in enumerate(shares):
        for share_index, share in enumerate(group):
            share_words = share.split(" ")
            while True:
                # display paginated share on the screen
                await _show_share_words(ctx, share_words, share_index, group_index)

                # make the user confirm words from the share
                if await _confirm_share_words(
                    ctx, share_index, share_words, group_index
                ):
                    await _show_confirmation_success(
                        ctx,
                        share_index=share_index,
                        num_of_shares=len(group),
                        group_index=group_index,
                    )
                    break  # this share is confirmed, go to next one
                else:
                    await _show_confirmation_failure(ctx, share_index)


class Slip39NumInput(ui.Component):
    SET_SHARES = object()
    SET_THRESHOLD = object()
    SET_GROUPS = object()
    SET_GROUP_THRESHOLD = object()

    def __init__(self, step, count, min_count, max_count, group_id=None):
        super().__init__()
        self.step = step
        self.input = NumInput(count, min_count=min_count, max_count=max_count)
        self.input.on_change = self.on_change
        self.group_id = group_id

    def dispatch(self, event, x, y):
        self.input.dispatch(event, x, y)
        if event is ui.RENDER:
            self.on_render()

    def on_render(self):
        if self.repaint:
            count = self.input.count

            # render the headline
            if self.step is Slip39NumInput.SET_SHARES:
                header = "Set num. of shares"
            elif self.step is Slip39NumInput.SET_THRESHOLD:
                header = "Set threshold"
            elif self.step is Slip39NumInput.SET_GROUPS:
                header = "Set num. of groups"
            elif self.step is Slip39NumInput.SET_GROUP_THRESHOLD:
                header = "Set group threshold"
            ui.header(header, ui.ICON_RESET, ui.TITLE_GREY, ui.BG, ui.ORANGE_ICON)

            # render the counter
            if self.step is Slip39NumInput.SET_SHARES:
                if self.group_id is None:
                    if count == 1:
                        first_line_text = "Only one share will"
                        second_line_text = "be created."
                    else:
                        first_line_text = "%s people or locations" % count
                        second_line_text = "will each hold one share."
                else:
                    first_line_text = "Set the total number of"
                    second_line_text = "shares in Group %s." % (self.group_id + 1)
                ui.display.bar(0, 110, ui.WIDTH, 52, ui.BG)
                ui.display.text(12, 130, first_line_text, ui.NORMAL, ui.FG, ui.BG)
                ui.display.text(12, 156, second_line_text, ui.NORMAL, ui.FG, ui.BG)
            elif self.step is Slip39NumInput.SET_THRESHOLD:
                if self.group_id is None:
                    first_line_text = "For recovery you need"
                    if count == 1:
                        second_line_text = "1 share."
                    elif count == self.input.max_count:
                        second_line_text = "all %s of the shares." % count
                    else:
                        second_line_text = "any %s of the shares." % count
                else:
                    first_line_text = "The required number of "
                    second_line_text = "shares to form Group %s." % (self.group_id + 1)
                ui.display.bar(0, 110, ui.WIDTH, 52, ui.BG)
                ui.display.text(12, 130, first_line_text, ui.NORMAL, ui.FG, ui.BG)
                ui.display.text(12, 156, second_line_text, ui.NORMAL, ui.FG, ui.BG)
            elif self.step is Slip39NumInput.SET_GROUPS:
                ui.display.bar(0, 110, ui.WIDTH, 52, ui.BG)
                ui.display.text(
                    12, 130, "A group is made up of", ui.NORMAL, ui.FG, ui.BG
                )
                ui.display.text(12, 156, "recovery shares.", ui.NORMAL, ui.FG, ui.BG)
            elif self.step is Slip39NumInput.SET_GROUP_THRESHOLD:
                ui.display.bar(0, 110, ui.WIDTH, 52, ui.BG)
                ui.display.text(
                    12, 130, "The required number of", ui.NORMAL, ui.FG, ui.BG
                )
                ui.display.text(
                    12, 156, "groups for recovery.", ui.NORMAL, ui.FG, ui.BG
                )

            self.repaint = False

    def on_change(self, count):
        self.repaint = True


class MnemonicWordSelect(ui.Layout):
    NUM_OF_CHOICES = 3

    def __init__(self, words, share_index, word_index, count, group_index=None):
        super().__init__()
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
        elif group_index is None:
            self.text = Text("Check share #%s" % (share_index + 1))
        else:
            self.text = Text(
                "Check G%s - Share %s" % ((group_index + 1), (share_index + 1))
            )
        self.text.normal("Select word %d of %d:" % (word_index + 1, count))

    def dispatch(self, event, x, y):
        for btn in self.buttons:
            btn.dispatch(event, x, y)
        self.text.dispatch(event, x, y)

    def select(self, word):
        def fn():
            raise ui.Result(word)

        return fn

    if __debug__:

        def read_content(self) -> List[str]:
            return self.text.read_content() + [b.text for b in self.buttons]

        def create_tasks(self) -> Tuple[loop.Task, ...]:
            return super().create_tasks() + (debug.input_signal(),)
