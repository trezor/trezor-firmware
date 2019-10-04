from trezor import ui, wire
from trezor.crypto.slip39 import MAX_SHARE_COUNT
from trezor.messages import BackupType, ButtonRequestType
from trezor.messages.ButtonAck import ButtonAck
from trezor.messages.ButtonRequest import ButtonRequest
from trezor.ui.scroll import Paginated
from trezor.ui.text import Text
from trezor.ui.word_select import WordSelector

from .keyboard_bip39 import Bip39Keyboard
from .keyboard_slip39 import Slip39Keyboard
from .recover import RecoveryAborted

from apps.common import storage
from apps.common.confirm import confirm, info_confirm, require_confirm
from apps.common.layout import show_success, show_warning
from apps.management import backup_types
from apps.management.recovery_device import recover

if __debug__:
    from apps.debug import input_signal

if False:
    from typing import List, Optional, Callable, Iterable, Tuple
    from trezor.messages.ResetDevice import EnumTypeBackupType


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
    ctx: wire.Context, word_count: int, backup_type: Optional[EnumTypeBackupType]
) -> Optional[str]:
    await ctx.call(ButtonRequest(code=ButtonRequestType.MnemonicInput), ButtonAck)

    words = []
    for i in range(word_count):
        if backup_types.is_slip39_word_count(word_count):
            keyboard = Slip39Keyboard("Type word %s of %s:" % (i + 1, word_count))
        else:
            keyboard = Bip39Keyboard("Type word %s of %s:" % (i + 1, word_count))
        if __debug__:
            word = await ctx.wait(keyboard, input_signal())
        else:
            word = await ctx.wait(keyboard)

        if not await check_word_validity(ctx, i, word, backup_type, words):
            return None

        words.append(word)

    return " ".join(words)


async def check_word_validity(
    ctx: wire.Context,
    current_index: int,
    current_word: str,
    backup_type: Optional[EnumTypeBackupType],
    previous_words: List[str],
) -> bool:
    # we can't perform any checks if the backup type was not yet decided
    if backup_type is None:
        return True
    # there are no "on-the-fly" checks for BIP-39
    if backup_type is BackupType.Bip39:
        return True

    previous_mnemonics = recover.fetch_previous_mnemonics()
    if previous_mnemonics is None:
        # this should not happen if backup_type is set
        raise RuntimeError

    if backup_type == BackupType.Slip39_Basic:
        # check if first 3 words of mnemonic match
        # we can check against the first one, others were checked already
        if current_index < 3:
            share_list = previous_mnemonics[0][0].split(" ")
            if share_list[current_index] != current_word:
                await show_identifier_mismatch(ctx)
                return False
        elif current_index == 3:
            for share in previous_mnemonics[0]:
                share_list = share.split(" ")
                # check if the fourth word is different from previous shares
                if share_list[current_index] == current_word:
                    await show_share_already_added(ctx)
                    return False
    elif backup_type == BackupType.Slip39_Advanced:
        # in case of advanced slip39 recovery we only check 2 words
        if current_index < 2:
            share_list = next(s for s in previous_mnemonics if s)[0].split(" ")
            if share_list[current_index] != current_word:
                await show_identifier_mismatch(ctx)
                return False
        # check if we reached threshold in group
        elif current_index == 2:
            for i, group in enumerate(previous_mnemonics):
                if len(group) > 0:
                    if current_word == group[0].split(" ")[current_index]:
                        remaining_shares = (
                            storage.recovery.fetch_slip39_remaining_shares()
                        )
                        if remaining_shares[i] == 0:
                            await show_group_threshold_reached(ctx)
                            return False
        # check if share was already added for group
        elif current_index == 3:
            # we use the 3rd word from previously entered shares to find the group id
            group_identifier_word = previous_words[2]
            group_index = None
            for i, group in enumerate(previous_mnemonics):
                if len(group) > 0:
                    if group_identifier_word == group[0].split(" ")[2]:
                        group_index = i

            if group_index:
                group = previous_mnemonics[group_index]
                for share in group:
                    if current_word == share.split(" ")[current_index]:
                        await show_share_already_added(ctx)
                        return False

    return True


async def show_remaining_shares(
    ctx: wire.Context,
    groups: Iterable[Tuple[int, Tuple[str]]],  # remaining + list 3 words
    shares_remaining: List[int],
    group_threshold: int,
) -> None:
    pages = []
    for remaining, group in groups:
        if 0 < remaining < MAX_SHARE_COUNT:
            text = Text("Remaining Shares")
            if remaining > 1:
                text.bold("%s more shares starting" % remaining)
            else:
                text.bold("%s more share starting" % remaining)
            for word in group:
                text.normal(word)
            pages.append(text)
        elif (
            remaining == MAX_SHARE_COUNT and shares_remaining.count(0) < group_threshold
        ):
            text = Text("Remaining Shares")
            groups_remaining = group_threshold - shares_remaining.count(0)
            if groups_remaining > 1:
                text.bold("%s more groups starting" % groups_remaining)
            elif groups_remaining > 0:
                text.bold("%s more group starting" % groups_remaining)
            for word in group:
                text.normal(word)
            pages.append(text)

    return await confirm(ctx, Paginated(pages), cancel=None)


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


async def show_invalid_mnemonic(ctx: wire.Context, word_count: int) -> None:
    if backup_types.is_slip39_word_count(word_count):
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
    ctx: wire.Context,
    homepage: RecoveryHomescreen,
    button_label: str,
    info_func: Callable = None,
) -> None:
    while True:
        if info_func:
            continue_recovery = await info_confirm(
                ctx,
                homepage,
                code=ButtonRequestType.RecoveryHomepage,
                confirm=button_label,
                info_func=info_func,
                info="Info",
                cancel="Abort",
            )
        else:
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
