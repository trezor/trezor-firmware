from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor import wire
    from typing import Iterable, Callable


async def request_word_count(ctx: wire.GenericContext, dry_run: bool) -> int:
    raise NotImplementedError


async def request_word(
    ctx: wire.GenericContext, word_index: int, word_count: int, is_slip39: bool
) -> str:
    raise NotImplementedError


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
) -> bool:
    raise NotImplementedError
