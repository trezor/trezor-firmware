from typing import TYPE_CHECKING

import trezorui2

from ..common import interact
from . import RustLayout

if TYPE_CHECKING:
    from typing import Iterable, Callable, Any

    pass


async def request_word_count(dry_run: bool) -> int:
    raise NotImplementedError


async def request_word(word_index: int, word_count: int, is_slip39: bool) -> str:
    if is_slip39:
        keyboard: Any = RustLayout(
            trezorui2.request_bip39(
                prompt=f"Type word {word_index + 1} of {word_count}:"
            )
        )
    else:
        keyboard = RustLayout(
            trezorui2.request_slip39(
                prompt=f"Type word {word_index + 1} of {word_count}:"
            )
        )

    word: str = await interact(keyboard, None)
    return word


async def show_remaining_shares(
    groups: Iterable[tuple[int, tuple[str, ...]]],  # remaining + list 3 words
    shares_remaining: list[int],
    group_threshold: int,
) -> None:
    raise NotImplementedError


async def show_group_share_success(share_index: int, group_index: int) -> None:
    raise NotImplementedError


async def continue_recovery(
    button_label: str,
    text: str,
    subtext: str | None,
    info_func: Callable | None,
) -> bool:
    raise NotImplementedError
