from typing import TYPE_CHECKING

from trezor.enums import ButtonRequestType

import trezorui2

from ..common import interact
from . import RustLayout, _placeholder_confirm, confirm_action, get_bool

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
    await _placeholder_confirm(
        ctx=ctx,
        br_type="backup_words",
        title="SHARE WORDS",
        description="Write all words in order on recovery seed card.",
        data="Do NOT make digital copies.",
        br_code=ButtonRequestType.ResetDevice,
    )

    # Showing words, asking for write down confirmation and preparing for check
    # until user accepts everything.
    while True:
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

        wrote_down = await get_bool(
            ctx=ctx,
            title="SHARE WORDS",
            data=f"I wrote down all {len(share_words)} words in order.",
            verb="I WROTE DOWN",
            hold=True,
            br_type="backup_words",
            br_code=ButtonRequestType.ResetDevice,
        )
        if not wrote_down:
            continue

        ready_to_check = await get_bool(
            ctx=ctx,
            title="CHECK PHRASE",
            data="Select correct words in correct positions.",
            verb_cancel="SEE AGAIN",
            verb="BEGIN",
            br_type="backup_words",
            br_code=ButtonRequestType.ResetDevice,
        )
        if not ready_to_check:
            continue

        # All went well, we can break the loop.
        break


async def select_word(
    ctx: wire.GenericContext,
    words: Sequence[str],
    share_index: int | None,
    checked_index: int,
    count: int,
    group_index: int | None = None,
) -> str:
    # TODO: it might not always be 3 words, it can happen it will be only two,
    # but the probability is very small - 4 words containing two items two times
    # (or one in "all all" seed)
    assert len(words) == 3
    result = await ctx.wait(
        RustLayout(
            trezorui2.select_word(
                title=f"SELECT WORD {checked_index + 1}/{count}",
                words=(words[0].upper(), words[1].upper(), words[2].upper()),
            )
        )
    )
    for word in words:
        if word.upper() == result:
            return word
    raise ValueError("Invalid word")


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
    await confirm_action(
        ctx,
        "backup_warning",
        "Caution",
        description="Never make a digital copy and never upload it online.",
        verb="I understand",
        verb_cancel=None,
        br_code=ButtonRequestType.ResetDevice,
    )
