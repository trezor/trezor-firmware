from trezor import ui, wire
from trezor.errors import IdentifierMismatchError, ShareAlreadyAddedError
from trezor.messages import BackupType, ButtonRequestType
from trezor.messages.ButtonAck import ButtonAck
from trezor.messages.ButtonRequest import ButtonRequest
from trezor.ui.info import InfoConfirm
from trezor.ui.scroll import Paginated
from trezor.ui.text import Text
from trezor.ui.word_select import WordSelector

from . import backup_types
from .keyboard_bip39 import Bip39Keyboard
from .keyboard_slip39 import Slip39Keyboard
from .recover import RecoveryAborted

from apps.common import storage
from apps.common.confirm import confirm, require_confirm
from apps.common.layout import show_success, show_warning

if __debug__:
    from apps.debug import input_signal, confirm_signal

if False:
    from typing import List


async def confirm_abort(ctx: wire.Context, dry_run: bool = False) -> bool:
    if dry_run:
        text = Text("Abort seed check", ui.ICON_WIPE)
        text.normal("Do you really want to", "abort the seed check?")
    else:
        text = Text("Abort recovery", ui.ICON_WIPE)
        text.normal("Do you really want to", "abort the recovery", "process?")
        text.bold("All progress will be lost.")
    return await confirm(ctx, text, code=ButtonRequestType.ProtectCall)


async def request_word_count(ctx: wire.Context, dry_run: bool) -> int:
    await ctx.call(ButtonRequest(code=ButtonRequestType.MnemonicWordCount), ButtonAck)

    if dry_run:
        text = Text("Seed check", ui.ICON_RECOVERY)
    else:
        text = Text("Recovery mode", ui.ICON_RECOVERY)
    text.normal("Number of words?")

    if __debug__:
        count = await ctx.wait(WordSelector(text), input_signal())
        count = int(count)  # if input_signal was triggered, count is a string
    else:
        count = await ctx.wait(WordSelector(text))

    return count


async def request_mnemonic(
    ctx: wire.Context,
    word_count: int,
    mnemonics: List[str],
    possible_backup_types: list,
) -> str:
    await ctx.call(ButtonRequest(code=ButtonRequestType.MnemonicInput), ButtonAck)

    words = []
    for i in range(word_count):
        if backup_types.is_slip39(possible_backup_types):
            keyboard = Slip39Keyboard("Type word %s of %s:" % (i + 1, word_count))
        else:
            keyboard = Bip39Keyboard("Type word %s of %s:" % (i + 1, word_count))
        if __debug__:
            word = await ctx.wait(keyboard, input_signal())
        else:
            word = await ctx.wait(keyboard)

        if mnemonics:
            if BackupType.Slip39_Basic in possible_backup_types:
                # check if first 3 words of mnemonic match
                # we can check against the first one, others were checked already
                if i < 3:
                    share_list = mnemonics[0].split(" ")
                    if share_list[i] != word:
                        raise IdentifierMismatchError()
                elif i == 3:
                    for share in mnemonics:
                        share_list = share.split(" ")
                        # check if the fourth word is different from previous shares
                        if share_list[i] == word:
                            raise ShareAlreadyAddedError()
            elif BackupType.Slip39_Advanced in possible_backup_types:
                # in case of advanced shamir recovery we only check 2 words
                if i < 2:
                    share_list = mnemonics[0].split(" ")
                    if share_list[i] != word:
                        raise IdentifierMismatchError()

        words.append(word)

    return " ".join(words)


async def show_remaining_shares(
    ctx: wire.Context,
    groups: List[[int, List[str]]],  # remaining + list 3 words
    group_threshold: int,
    shares_remaining: List[int],
) -> None:
    pages = []
    for remaining, group in groups:
        if 0 < remaining < 16:
            text = Text("Remaining Shares")
            if remaining > 1:
                text.bold("%s more shares starting" % remaining)
            else:
                text.bold("%s more share starting" % remaining)
            for word in group:
                text.normal(word)
            pages.append(text)
        elif remaining == 16 and shares_remaining.count(0) < group_threshold:
            text = Text("Remaining Shares")
            groups_remaining = group_threshold - shares_remaining.count(0)
            if groups_remaining > 1:
                text.bold("%s more groups starting" % groups_remaining)
            elif groups_remaining > 0:
                text.bold("%s more group starting" % groups_remaining)
            for word in group:
                text.normal(word)
            pages.append(text)

    return await confirm(ctx, Paginated(pages), confirm="Continue", cancel=None)


async def show_group_share_success(
    ctx: wire.Context, share_index: int, group_index: int
) -> None:
    text = Text("Success", ui.ICON_CONFIRM)
    text.bold("You have entered")
    text.bold("Share %s" % (share_index + 1))
    text.normal("from")
    text.bold("Group %s" % (group_index + 1))

    return await confirm(ctx, text, confirm="Continue", cancel=None)


async def show_dry_run_result(ctx: wire.Context, result: bool, is_slip39: bool) -> None:
    if result:
        if is_slip39:
            text = (
                "The entered recovery",
                "shares are valid and",
                "match what is currently",
                "in the device.",
            )
        else:
            text = (
                "The entered recovery",
                "seed is valid and",
                "matches the one",
                "in the device.",
            )
        await show_success(ctx, text, button="Continue")
    else:
        if is_slip39:
            text = (
                "The entered recovery",
                "shares are valid but",
                "do not match what is",
                "currently in the device.",
            )
        else:
            text = (
                "The entered recovery",
                "seed is valid but does",
                "not match the one",
                "in the device.",
            )
        await show_warning(ctx, text, button="Continue")


async def show_dry_run_different_type(ctx: wire.Context) -> None:
    text = Text("Dry run failure", ui.ICON_CANCEL)
    text.normal("Seed in the device was")
    text.normal("created using another")
    text.normal("backup mechanism.")
    await require_confirm(
        ctx, text, ButtonRequestType.ProtectCall, cancel=None, confirm="Continue"
    )


async def show_keyboard_info(ctx: wire.Context) -> None:
    # TODO: do not send ButtonRequestType.Other
    await ctx.call(ButtonRequest(code=ButtonRequestType.Other), ButtonAck)

    info = InfoConfirm(
        "Did you know? "
        "You can type the letters "
        "one by one or use it like "
        "a T9 keyboard.",
        "Great!",
    )
    if __debug__:
        await ctx.wait(info, confirm_signal())
    else:
        await ctx.wait(info)


async def show_invalid_mnemonic(ctx: wire.Context, is_slip39: bool) -> None:
    if is_slip39:
        await show_warning(ctx, ("You have entered", "an invalid recovery", "share."))
    else:
        await show_warning(ctx, ("You have entered", "an invalid recovery", "seed."))


async def show_share_already_added(ctx: wire.Context) -> None:
    await show_warning(
        ctx, ("Share already entered,", "please enter", "a different share.")
    )


async def show_identifier_mismatch(ctx: wire.Context) -> None:
    await show_warning(
        ctx, ("You have entered", "a share from another", "Shamir Backup.")
    )


async def show_group_threshold_reached(ctx: wire.Context) -> None:
    await show_warning(
        ctx,
        (
            "Threshold of this",
            "group has been reached.",
            "Input share from",
            "different group",
        ),
    )


class RecoveryHomescreen(ui.Component):
    def __init__(self, text: str, subtext: str = None):
        self.text = text
        self.subtext = subtext
        self.dry_run = storage.recovery.is_dry_run()
        self.repaint = True

    def on_render(self) -> None:
        if not self.repaint:
            return

        if self.dry_run:
            heading = "SEED CHECK"
        else:
            heading = "RECOVERY MODE"
        ui.header_warning(heading, clear=False)

        if not self.subtext:
            ui.display.text_center(ui.WIDTH // 2, 80, self.text, ui.BOLD, ui.FG, ui.BG)
        else:
            ui.display.text_center(ui.WIDTH // 2, 65, self.text, ui.BOLD, ui.FG, ui.BG)
            ui.display.text_center(
                ui.WIDTH // 2, 92, self.subtext, ui.NORMAL, ui.FG, ui.BG
            )

        ui.display.text_center(
            ui.WIDTH // 2, 130, "It is safe to eject Trezor", ui.NORMAL, ui.GREY, ui.BG
        )
        ui.display.text_center(
            ui.WIDTH // 2, 155, "and continue later", ui.NORMAL, ui.GREY, ui.BG
        )

        self.repaint = False


async def homescreen_dialog(
    ctx: wire.Context, homepage: RecoveryHomescreen, button_label: str
) -> None:
    while True:
        continue_recovery = await confirm(
            ctx,
            homepage,
            code=ButtonRequestType.RecoveryHomepage,
            confirm=button_label,
            major_confirm=True,
        )
        if continue_recovery:
            # go forward in the recovery process
            break
        # user has chosen to abort, confirm the choice
        dry_run = storage.recovery.is_dry_run()
        if await confirm_abort(ctx, dry_run):
            raise RecoveryAborted
