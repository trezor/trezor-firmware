from typing import TYPE_CHECKING

from trezor.crypto import random
from trezor.enums import ButtonRequestType

import trezorui2

from ..common import interact
from . import RustLayout

if TYPE_CHECKING:
    from trezor import wire
    from trezor.enums import BackupType
    from typing import Sequence


async def show_share_words(
    ctx: wire.GenericContext,
    share_words: Sequence[str],
    share_index: int | None = None,
    group_index: int | None = None,
) -> None:
    await interact(
        ctx,
        RustLayout(
            trezorui2.show_share_words(
                share_words=share_words,
            )
        ),
        br_type="backup_words",
        br_code=ButtonRequestType.ResetDevice,
    )


async def confirm_word(
    ctx: wire.GenericContext,
    share_index: int | None,
    share_words: Sequence[str],
    offset: int,
    count: int,
    group_index: int | None = None,
) -> bool:
    # remove duplicates
    non_duplicates = list(set(share_words))
    # shuffle list
    random.shuffle(non_duplicates)
    # take top 3 words
    choices = non_duplicates[:3]
    # select first of them
    checked_word = choices[0]
    # find its index
    checked_index = share_words.index(checked_word) + offset
    # shuffle again so the confirmed word is not always the first choice
    random.shuffle(choices)

    selected_word = await interact(
        ctx,
        RustLayout(
            trezorui2.confirm_word(
                choices=choices,
                share_index=share_index,
                checked_index=checked_index,
                count=count,
                group_index=group_index,
            )
        ),
        br_type="backup_words",
        br_code=ButtonRequestType.ResetDevice,
    )

    # confirm it is the correct one
    return selected_word == checked_word


async def slip39_show_checklist(
    ctx: wire.GenericContext, step: int, backup_type: BackupType
) -> None:
    raise NotImplementedError


async def slip39_prompt_threshold(
    ctx: wire.GenericContext, num_of_shares: int, group_id: int | None = None
) -> int:
    raise NotImplementedError


async def slip39_prompt_number_of_shares(
    ctx: wire.GenericContext, group_id: int | None = None
) -> int:
    raise NotImplementedError


async def slip39_advanced_prompt_number_of_groups(ctx: wire.GenericContext) -> int:
    raise NotImplementedError


async def slip39_advanced_prompt_group_threshold(
    ctx: wire.GenericContext, num_of_groups: int
) -> int:
    raise NotImplementedError
