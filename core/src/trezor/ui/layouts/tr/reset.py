from typing import TYPE_CHECKING

from trezor.enums import ButtonRequestType

import trezorui2

from ..common import interact
from . import RustLayout, confirm_action

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


async def select_word(
    ctx: wire.GenericContext,
    words: Sequence[str],
    share_index: int | None,
    checked_index: int,
    count: int,
    group_index: int | None = None,
) -> str:
    assert len(words) == 3
    if share_index is None:
        title: str = "CHECK SEED"
    elif group_index is None:
        title = f"CHECK SHARE #{share_index + 1}"
    else:
        title = f"CHECK G{group_index + 1} - SHARE {share_index + 1}"

    result = await ctx.wait(
        RustLayout(
            trezorui2.select_word(
                title=title,
                description=f"Select word {checked_index + 1}/{count}",
                words=(words[0].upper(), words[1].upper(), words[2].upper()),
            )
        )
    )
    if __debug__ and isinstance(result, str):
        return result
    assert isinstance(result, int) and 0 <= result <= 2
    return words[result]


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


async def show_warning_backup(ctx: wire.GenericContext, slip39: bool) -> None:
    if slip39:
        description = (
            "Never make a digital copy of your shares and never upload them online."
        )
    else:
        description = (
            "Never make a digital copy of your seed and never upload it online."
        )
    await confirm_action(
        ctx,
        "backup_warning",
        "Caution",
        description=description,
        verb="I understand",
        verb_cancel=None,
        br_code=ButtonRequestType.ResetDevice,
    )
