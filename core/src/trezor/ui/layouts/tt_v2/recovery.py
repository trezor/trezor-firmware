from typing import Callable, Iterable

import trezorui2
from trezor.enums import ButtonRequestType
from trezor.wire.context import wait as ctx_wait

from ..common import interact
from . import RustLayout, raise_if_not_confirmed

CONFIRMED = trezorui2.CONFIRMED  # global_import_cache
INFO = trezorui2.INFO  # global_import_cache


async def _is_confirmed_info(
    dialog: RustLayout,
    info_func: Callable,
) -> bool:
    while True:
        result = await ctx_wait(dialog)

        if result is trezorui2.INFO:
            await info_func()
        else:
            return result is CONFIRMED


async def request_word_count(dry_run: bool) -> int:
    selector = RustLayout(trezorui2.select_word_count(dry_run=dry_run))
    count = await interact(selector, "word_count", ButtonRequestType.MnemonicWordCount)
    return int(count)


async def request_word(word_index: int, word_count: int, is_slip39: bool) -> str:
    prompt = f"Type word {word_index + 1} of {word_count}"
    if is_slip39:
        keyboard = RustLayout(trezorui2.request_slip39(prompt=prompt))
    else:
        keyboard = RustLayout(trezorui2.request_bip39(prompt=prompt))

    word: str = await ctx_wait(keyboard)
    return word


async def show_remaining_shares(
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

    await raise_if_not_confirmed(
        interact(
            RustLayout(trezorui2.show_remaining_shares(pages=pages)),
            "show_shares",
            ButtonRequestType.Other,
        )
    )


async def show_group_share_success(share_index: int, group_index: int) -> None:
    await raise_if_not_confirmed(
        interact(
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
    )


async def continue_recovery(
    button_label: str,
    text: str,
    subtext: str | None,
    info_func: Callable | None,
    dry_run: bool,
    show_info: bool = False,  # unused on TT
) -> bool:
    from ..common import button_request

    if show_info:
        # Show this just one-time
        description = "You'll only have to select the first 2-3 letters of each word."
    else:
        description = subtext or ""

    homepage = RustLayout(
        trezorui2.confirm_recovery(
            title=text,
            description=description,
            button=button_label.upper(),
            info_button=info_func is not None,
            dry_run=dry_run,
        )
    )

    await button_request("recovery", ButtonRequestType.RecoveryHomepage)

    if info_func is not None:
        return await _is_confirmed_info(homepage, info_func)
    else:
        result = await ctx_wait(homepage)
        return result is CONFIRMED


async def show_recovery_warning(
    br_type: str,
    content: str,
    subheader: str | None = None,
    button: str = "TRY AGAIN",
    br_code: ButtonRequestType = ButtonRequestType.Warning,
) -> None:
    await raise_if_not_confirmed(
        interact(
            RustLayout(
                trezorui2.show_warning(
                    title=content,
                    description=subheader or "",
                    button=button.upper(),
                    allow_cancel=False,
                )
            ),
            br_type,
            br_code,
        )
    )
