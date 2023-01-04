from typing import TYPE_CHECKING

from trezor.enums import ButtonRequestType

import trezorui2

from ..common import button_request, interact
from . import RustLayout, get_bool

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
    # It can be returning a string
    return int(count)


async def request_word(
    ctx: wire.GenericContext, word_index: int, word_count: int, is_slip39: bool
) -> str:
    prompt = f"WORD {word_index + 1} OF {word_count}"

    if is_slip39:
        raise NotImplementedError
    else:
        word = await interact(
            ctx,
            RustLayout(trezorui2.request_word_bip39(prompt=prompt)),
            "request_word",
            ButtonRequestType.MnemonicInput,
        )

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
    raise NotImplementedError


async def continue_recovery(
    ctx: wire.GenericContext,
    button_label: str,
    text: str,
    subtext: str | None,
    info_func: Callable | None,
    dry_run: bool,
) -> bool:
    # NOTE: no need to implement `info_func`, as it is used only in
    # Shamir backup, which is not implemented for TR.

    description = text
    if subtext:
        description += f"\n\n{subtext}"
    return await get_bool(
        ctx,
        "recovery",
        "START RECOVERY",
        None,
        description,
        verb="HOLD TO BEGIN",
        hold=True,
        br_code=ButtonRequestType.RecoveryHomepage,
    )
