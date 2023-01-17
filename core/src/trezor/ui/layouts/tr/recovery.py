from typing import TYPE_CHECKING

from trezor.enums import ButtonRequestType

import trezorui2

from ..common import button_request, interact
from . import RustLayout, raise_if_not_confirmed

if TYPE_CHECKING:
    from trezor import wire
    from typing import Iterable, Callable


async def request_word_count(ctx: wire.GenericContext, dry_run: bool) -> int:
    await button_request(ctx, "word_count", code=ButtonRequestType.MnemonicWordCount)
    count = await interact(
        ctx,
        RustLayout(trezorui2.select_word_count(dry_run=dry_run)),
        "word_count",
        ButtonRequestType.MnemonicWordCount,
    )
    # It can be returning a string (for example for __debug__ in tests)
    return int(count)


async def request_word(
    ctx: wire.GenericContext, word_index: int, word_count: int, is_slip39: bool
) -> str:
    prompt = f"WORD {word_index + 1} OF {word_count}"

    if is_slip39:
        word_choice = RustLayout(trezorui2.request_slip39(prompt=prompt))
    else:
        word_choice = RustLayout(trezorui2.request_bip39(prompt=prompt))

    word: str = await ctx.wait(word_choice)
    return word


async def show_remaining_shares(
    ctx: wire.GenericContext,
    groups: Iterable[tuple[int, tuple[str, ...]]],  # remaining + list 3 words
    shares_remaining: list[int],
    group_threshold: int,
) -> None:
    raise NotImplementedError


async def show_group_share_success(
    ctx: wire.GenericContext, share_index: int, group_index: int
) -> None:
    await raise_if_not_confirmed(
        interact(
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
    )


async def continue_recovery(
    ctx: wire.GenericContext,
    button_label: str,
    text: str,
    subtext: str | None,
    info_func: Callable | None,
    dry_run: bool,
) -> bool:
    # TODO: implement info_func?
    # There is very limited space on the screen
    # (and having middle button would mean shortening the right button text)

    description = text
    if subtext:
        description += f"\n\n{subtext}"

    homepage = RustLayout(
        trezorui2.confirm_recovery(
            title="",
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
