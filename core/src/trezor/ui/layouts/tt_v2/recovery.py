from typing import TYPE_CHECKING

from trezor import strings, wire
from trezor.crypto.slip39 import MAX_SHARE_COUNT
from trezor.enums import ButtonRequestType

import trezorui2

from ..common import button_request, interact
from . import _RustLayout

if TYPE_CHECKING:
    from typing import Iterable, Callable, Any

    pass


async def _is_confirmed_info(
    ctx: wire.GenericContext,
    dialog: _RustLayout,
    info_func: Callable,
) -> bool:
    while True:
        result = await ctx.wait(dialog)

        if result is trezorui2.INFO:
            await info_func(ctx)
        else:
            return result is trezorui2.CONFIRMED


async def request_word_count(ctx: wire.GenericContext, dry_run: bool) -> int:
    selector = _RustLayout(trezorui2.select_word_count(dry_run=dry_run))
    count = await interact(
        ctx, selector, "word_count", ButtonRequestType.MnemonicWordCount
    )
    return int(count)


async def request_word(
    ctx: wire.GenericContext, word_index: int, word_count: int, is_slip39: bool
) -> str:
    if is_slip39:
        keyboard: Any = _RustLayout(
            trezorui2.request_bip39(
                prompt=f"Type word {word_index + 1} of {word_count}:"
            )
        )
    else:
        keyboard = _RustLayout(
            trezorui2.request_slip39(
                prompt=f"Type word {word_index + 1} of {word_count}:"
            )
        )

    word: str = await ctx.wait(keyboard)
    return word


async def show_remaining_shares(
    ctx: wire.GenericContext,
    groups: Iterable[tuple[int, tuple[str, ...]]],  # remaining + list 3 words
    shares_remaining: list[int],
    group_threshold: int,
) -> None:
    pages: list[tuple[str, str]] = []
    for remaining, group in groups:
        if 0 < remaining < MAX_SHARE_COUNT:
            title = strings.format_plural(
                "{count} more {plural} starting", remaining, "share"
            )
            words = "\n".join(group)
            pages.append((title, words))
        elif (
            remaining == MAX_SHARE_COUNT and shares_remaining.count(0) < group_threshold
        ):
            groups_remaining = group_threshold - shares_remaining.count(0)
            title = strings.format_plural(
                "{count} more {plural} starting", groups_remaining, "group"
            )
            words = "\n".join(group)
            pages.append((title, words))

    result = await interact(
        ctx,
        _RustLayout(trezorui2.show_remaining_shares(pages=pages)),
        "show_shares",
        ButtonRequestType.Other,
    )
    if result is not trezorui2.CONFIRMED:
        raise wire.ActionCancelled


async def show_group_share_success(
    ctx: wire.GenericContext, share_index: int, group_index: int
) -> None:
    result = await interact(
        ctx,
        _RustLayout(
            trezorui2.show_group_share_success(
                lines=[
                    "You have entered",
                    f"Share {share_index + 1}",
                    "from",
                    f"Group {group_index + 1}",
                ],
            )
        ),
        "share_success",
        ButtonRequestType.Other,
    )
    if result is not trezorui2.CONFIRMED:
        raise wire.ActionCancelled


async def continue_recovery(
    ctx: wire.GenericContext,
    button_label: str,
    text: str,
    subtext: str | None,
    info_func: Callable | None,
    dry_run: bool,
) -> bool:
    title = text
    if subtext:
        title += "\n"
        title += subtext

    description = "It is safe to eject Trezor\nand continue later"

    if info_func is not None:
        homepage = _RustLayout(
            trezorui2.confirm_recovery(
                title=title,
                description=description,
                button=button_label.upper(),
                info_button=True,
                dry_run=dry_run,
            )
        )
        await button_request(ctx, "recovery", ButtonRequestType.RecoveryHomepage)
        return await _is_confirmed_info(ctx, homepage, info_func)
    else:
        homepage = _RustLayout(
            trezorui2.confirm_recovery(
                title=text,
                description=description,
                button=button_label.upper(),
                info_button=False,
                dry_run=dry_run,
            )
        )
        result = await interact(
            ctx,
            homepage,
            "recovery",
            ButtonRequestType.RecoveryHomepage,
        )
        return result is trezorui2.CONFIRMED
