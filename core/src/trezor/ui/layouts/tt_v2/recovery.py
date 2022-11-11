from typing import TYPE_CHECKING

from trezor.enums import ButtonRequestType
from trezor.wire import ActionCancelled

import trezorui2

from ..common import interact
from . import RustLayout

if TYPE_CHECKING:
    from typing import Iterable, Callable
    from trezor.wire import GenericContext


CONFIRMED = trezorui2.CONFIRMED  # global_import_cache
INFO = trezorui2.INFO  # global_import_cache


async def _is_confirmed_info(
    ctx: GenericContext,
    dialog: RustLayout,
    info_func: Callable,
) -> bool:
    while True:
        result = await ctx.wait(dialog)

        if result is trezorui2.INFO:
            await info_func(ctx)
        else:
            return result is CONFIRMED


async def request_word_count(ctx: GenericContext, dry_run: bool) -> int:
    selector = RustLayout(trezorui2.select_word_count(dry_run=dry_run))
    count = await interact(
        ctx, selector, "word_count", ButtonRequestType.MnemonicWordCount
    )
    return int(count)


async def request_word(
    ctx: GenericContext, word_index: int, word_count: int, is_slip39: bool
) -> str:
    prompt = f"Type word {word_index + 1} of {word_count}:"
    if is_slip39:
        keyboard = RustLayout(trezorui2.request_slip39(prompt=prompt))
    else:
        keyboard = RustLayout(trezorui2.request_bip39(prompt=prompt))

    word: str = await ctx.wait(keyboard)
    return word


async def show_remaining_shares(
    ctx: GenericContext,
    groups: Iterable[tuple[int, tuple[str, ...]]],  # remaining + list 3 words
    shares_remaining: list[int],
    group_threshold: int,
) -> None:
    from trezor import strings
    from trezor.crypto.slip39 import MAX_SHARE_COUNT

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
        RustLayout(trezorui2.show_remaining_shares(pages=pages)),
        "show_shares",
        ButtonRequestType.Other,
    )
    if result is not CONFIRMED:
        raise ActionCancelled


async def show_group_share_success(
    ctx: GenericContext, share_index: int, group_index: int
) -> None:
    result = await interact(
        ctx,
        RustLayout(
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
    if result is not CONFIRMED:
        raise ActionCancelled


async def continue_recovery(
    ctx: GenericContext,
    button_label: str,
    text: str,
    subtext: str | None,
    info_func: Callable | None,
    dry_run: bool,
) -> bool:
    from ..common import button_request

    title = text
    if subtext:
        title += "\n"
        title += subtext

    description = "It is safe to eject Trezor\nand continue later"

    if info_func is not None:
        homepage = RustLayout(
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
        homepage = RustLayout(
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
        return result is CONFIRMED
