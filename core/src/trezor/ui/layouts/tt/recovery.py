from trezor import strings, ui, wire
from trezor.crypto.slip39 import MAX_SHARE_COUNT
from trezor.enums import ButtonRequestType

from ...components.common.confirm import (
    is_confirmed,
    is_confirmed_info,
    raise_if_cancelled,
)
from ...components.tt.confirm import Confirm, InfoConfirm
from ...components.tt.keyboard_bip39 import Bip39Keyboard
from ...components.tt.keyboard_slip39 import Slip39Keyboard
from ...components.tt.recovery import RecoveryHomescreen
from ...components.tt.scroll import Paginated
from ...components.tt.text import Text
from ...components.tt.word_select import WordSelector
from ..common import button_request, interact

if False:
    from typing import Callable, Iterable


async def request_word_count(ctx: wire.GenericContext, dry_run: bool) -> int:
    await button_request(ctx, "word_count", code=ButtonRequestType.MnemonicWordCount)

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


async def request_word(
    ctx: wire.GenericContext, word_index: int, word_count: int, is_slip39: bool
) -> str:
    if is_slip39:
        keyboard: Slip39Keyboard | Bip39Keyboard = Slip39Keyboard(
            f"Type word {word_index + 1} of {word_count}:"
        )
    else:
        keyboard = Bip39Keyboard(f"Type word {word_index + 1} of {word_count}:")

    word: str = await ctx.wait(keyboard)
    return word


async def show_remaining_shares(
    ctx: wire.GenericContext,
    groups: Iterable[tuple[int, tuple[str, ...]]],  # remaining + list 3 words
    shares_remaining: list[int],
    group_threshold: int,
) -> None:
    pages: list[ui.Component] = []
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

    pages[-1] = Confirm(pages[-1], cancel=None)
    await raise_if_cancelled(
        interact(ctx, Paginated(pages), "show_shares", ButtonRequestType.Other)
    )


async def show_group_share_success(
    ctx: wire.GenericContext, share_index: int, group_index: int
) -> None:
    text = Text("Success", ui.ICON_CONFIRM)
    text.bold("You have entered")
    text.bold(f"Share {share_index + 1}")
    text.normal("from")
    text.bold(f"Group {group_index + 1}")

    await raise_if_cancelled(
        interact(
            ctx,
            Confirm(text, confirm="Continue", cancel=None),
            "share_success",
            ButtonRequestType.Other,
        )
    )


async def continue_recovery(
    ctx: wire.GenericContext,
    button_label: str,
    text: str,
    subtext: str | None,
    info_func: Callable | None,
) -> bool:
    homepage = RecoveryHomescreen(text, subtext)
    if info_func is not None:
        content = InfoConfirm(
            homepage,
            confirm=button_label,
            info="Info",
            cancel="Abort",
        )
        await button_request(ctx, "recovery", ButtonRequestType.RecoveryHomepage)
        return await is_confirmed_info(ctx, content, info_func)
    else:
        return is_confirmed(
            await interact(
                ctx,
                Confirm(homepage, confirm=button_label, major_confirm=True),
                "recovery",
                ButtonRequestType.RecoveryHomepage,
            )
        )
