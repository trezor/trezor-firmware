from typing import TYPE_CHECKING

from trezor.enums import ButtonRequestType

import trezorui2

from ..common import button_request, interact
from . import RustLayout, confirm_action, get_bool

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
    await confirm_action(
        ctx,
        "share_success",
        "Success",
        description=f"You have entered\nShare {share_index + 1} from\nGroup {group_index + 1}",
        verb="CONTINUE",
        verb_cancel=None,
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

    if dry_run:
        title = "SEED CHECK"
    else:
        title = "RECOVERY MODE"

    return await get_bool(
        ctx,
        "recovery",
        title,
        None,
        description,
        verb=button_label.upper(),
        br_code=ButtonRequestType.RecoveryHomepage,
    )
