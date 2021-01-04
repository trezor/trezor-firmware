import storage.recovery
from trezor import strings, ui, wire
from trezor.crypto.slip39 import MAX_SHARE_COUNT
from trezor.messages import ButtonRequestType
from trezor.ui.components.tt.scroll import Paginated
from trezor.ui.components.tt.text import Text
from trezor.ui.components.tt.word_select import WordSelector
from trezor.ui.layouts import require, show_success, show_warning

from apps.common import button_request
from apps.common.confirm import confirm, info_confirm, require_confirm

from .. import backup_types
from . import word_validity
from .keyboard_bip39 import Bip39Keyboard
from .keyboard_slip39 import Slip39Keyboard
from .recover import RecoveryAborted

if False:
    from typing import List, Optional, Callable, Iterable, Tuple, Union
    from trezor.messages.ResetDevice import EnumTypeBackupType


async def confirm_abort(ctx: wire.GenericContext, dry_run: bool = False) -> bool:
    if dry_run:
        text = Text("Abort seed check", ui.ICON_WIPE)
        text.normal("Do you really want to", "abort the seed check?")
    else:
        text = Text("Abort recovery", ui.ICON_WIPE)
        text.normal("Do you really want to", "abort the recovery", "process?")
        text.bold("All progress will be lost.")
    return await confirm(ctx, text, code=ButtonRequestType.ProtectCall)


async def request_word_count(ctx: wire.GenericContext, dry_run: bool) -> int:
    await button_request(ctx, code=ButtonRequestType.MnemonicWordCount)

    if dry_run:
        text = Text("Seed check", ui.ICON_RECOVERY)
    else:
        text = Text("Recovery mode", ui.ICON_RECOVERY)
    text.normal("Number of words?")

    count = await ctx.wait(WordSelector(text))
    # WordSelector can return int, or string if the value came from debuglink
    # ctx.wait has a return type Any
    # Hence, it is easier to convert the returned value to int explicitly
    return int(count)


async def request_mnemonic(
    ctx: wire.GenericContext, word_count: int, backup_type: Optional[EnumTypeBackupType]
) -> Optional[str]:
    await button_request(ctx, code=ButtonRequestType.MnemonicInput)

    words: List[str] = []
    for i in range(word_count):
        if backup_types.is_slip39_word_count(word_count):
            keyboard: Union[Slip39Keyboard, Bip39Keyboard] = Slip39Keyboard(
                "Type word %s of %s:" % (i + 1, word_count)
            )
        else:
            keyboard = Bip39Keyboard("Type word %s of %s:" % (i + 1, word_count))

        word = await ctx.wait(keyboard)
        words.append(word)

        try:
            word_validity.check(backup_type, words)
        except word_validity.AlreadyAdded:
            await show_share_already_added(ctx)
            return None
        except word_validity.IdentifierMismatch:
            await show_identifier_mismatch(ctx)
            return None
        except word_validity.ThresholdReached:
            await show_group_threshold_reached(ctx)
            return None

    return " ".join(words)


async def show_remaining_shares(
    ctx: wire.GenericContext,
    groups: Iterable[Tuple[int, Tuple[str, ...]]],  # remaining + list 3 words
    shares_remaining: List[int],
    group_threshold: int,
) -> None:
    pages: List[ui.Component] = []
    for remaining, group in groups:
        if 0 < remaining < MAX_SHARE_COUNT:
            text = Text("Remaining Shares")
            text.bold(
                strings.format_plural(
                    "{count} more {plural} starting", remaining, "share"
                )
            )
            for word in group:
                text.normal(word)
            pages.append(text)
        elif (
            remaining == MAX_SHARE_COUNT and shares_remaining.count(0) < group_threshold
        ):
            text = Text("Remaining Shares")
            groups_remaining = group_threshold - shares_remaining.count(0)
            text.bold(
                strings.format_plural(
                    "{count} more {plural} starting", groups_remaining, "group"
                )
            )
            for word in group:
                text.normal(word)
            pages.append(text)
    await confirm(ctx, Paginated(pages), cancel=None)


async def show_group_share_success(
    ctx: wire.GenericContext, share_index: int, group_index: int
) -> None:
    text = Text("Success", ui.ICON_CONFIRM)
    text.bold("You have entered")
    text.bold("Share %s" % (share_index + 1))
    text.normal("from")
    text.bold("Group %s" % (group_index + 1))

    await confirm(ctx, text, confirm="Continue", cancel=None)


async def show_dry_run_result(
    ctx: wire.GenericContext, result: bool, is_slip39: bool
) -> None:
    if result:
        if is_slip39:
            text = "The entered recovery\nshares are valid and\nmatch what is currently\nin the device."
        else:
            text = "The entered recovery\nseed is valid and\nmatches the one\nin the device."
        await require(
            show_success(ctx, "success_dry_recovery", text, button="Continue")
        )
    else:
        if is_slip39:
            text = "The entered recovery\nshares are valid but\ndo not match what is\ncurrently in the device."
        else:
            text = "The entered recovery\nseed is valid but does\nnot match the one\nin the device."
        await require(
            show_warning(ctx, "warning_dry_recovery", text, button="Continue")
        )


async def show_dry_run_different_type(ctx: wire.GenericContext) -> None:
    text = Text("Dry run failure", ui.ICON_CANCEL)
    text.normal("Seed in the device was")
    text.normal("created using another")
    text.normal("backup mechanism.")
    await require_confirm(
        ctx, text, ButtonRequestType.ProtectCall, cancel=None, confirm="Continue"
    )


async def show_invalid_mnemonic(ctx: wire.GenericContext, word_count: int) -> None:
    if backup_types.is_slip39_word_count(word_count):
        await require(
            show_warning(
                ctx,
                "warning_invalid_share",
                "You have entered\nan invalid recovery\nshare.",
            )
        )
    else:
        await require(
            show_warning(
                ctx,
                "warning_invalid_seed",
                "You have entered\nan invalid recovery\nseed.",
            )
        )


async def show_share_already_added(ctx: wire.GenericContext) -> None:
    await require(
        show_warning(
            ctx,
            "warning_known_share",
            "Share already entered,\nplease enter\na different share.",
        )
    )


async def show_identifier_mismatch(ctx: wire.GenericContext) -> None:
    await require(
        show_warning(
            ctx,
            "warning_mismatched_share",
            "You have entered\na share from another\nShamir Backup.",
        )
    )


async def show_group_threshold_reached(ctx: wire.GenericContext) -> None:
    await require(
        show_warning(
            ctx,
            "warning_group_threshold",
            "Threshold of this\ngroup has been reached.\nInput share from\ndifferent group.",
        )
    )


class RecoveryHomescreen(ui.Component):
    def __init__(self, text: str, subtext: str = None):
        super().__init__()
        self.text = text
        self.subtext = subtext
        self.dry_run = storage.recovery.is_dry_run()

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

    if __debug__:

        def read_content(self) -> List[str]:
            return [self.__class__.__name__, self.text, self.subtext or ""]


async def homescreen_dialog(
    ctx: wire.GenericContext,
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
