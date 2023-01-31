from typing import TYPE_CHECKING

from trezor.enums import ButtonRequestType
from trezor.wire import ActionCancelled

import trezorui2

from ..common import interact
from . import RustLayout, confirm_action

CONFIRMED = trezorui2.CONFIRMED  # global_import_cache

if TYPE_CHECKING:
    from trezor.wire import GenericContext
    from trezor.enums import BackupType
    from typing import Sequence


async def show_share_words(
    ctx: GenericContext,
    share_words: Sequence[str],
    share_index: int | None = None,
    group_index: int | None = None,
) -> None:
    from . import get_bool

    if share_index is None:
        title = "RECOVERY SEED"
    elif group_index is None:
        title = f"SHARE #{share_index + 1}"
    else:
        title = f"G{group_index + 1} - SHARE {share_index + 1}"

    # Showing words, asking for write down confirmation and preparing for check
    # until user accepts everything.
    while True:
        await interact(
            ctx,
            RustLayout(
                trezorui2.show_share_words(  # type: ignore [Argument missing for parameter "pages"]
                    title=title,
                    share_words=share_words,  # type: ignore [No parameter named "share_words"]
                )
            ),
            "backup_words",
            ButtonRequestType.ResetDevice,
        )

        if share_index is None:
            check_title = "CHECK BACKUP"
        elif group_index is None:
            check_title = f"CHECK SHARE #{share_index + 1}"
        else:
            check_title = f"GROUP {group_index + 1} - SHARE {share_index + 1}"

        if await get_bool(
            ctx,
            "backup_words",
            check_title,
            None,
            "Select correct word for each position.",
            verb_cancel="SEE AGAIN",
            verb="BEGIN",
            br_code=ButtonRequestType.ResetDevice,
        ):
            # All went well, we can break the loop.
            break


async def select_word(
    ctx: GenericContext,
    words: Sequence[str],
    share_index: int | None,
    checked_index: int,
    count: int,
    group_index: int | None = None,
) -> str:
    from trezor.strings import format_ordinal

    # It may happen (with a very low probability)
    # that there will be less than three unique words to choose from.
    # In that case, duplicating the last word to make it three.
    words = list(words)
    while len(words) < 3:
        words.append(words[-1])

    result = await ctx.wait(
        RustLayout(
            trezorui2.select_word(
                title="",
                description=f"SELECT {format_ordinal(checked_index + 1).upper()} WORD",
                words=(words[0].lower(), words[1].lower(), words[2].lower()),
            )
        )
    )
    if __debug__ and isinstance(result, str):
        return result
    assert isinstance(result, int) and 0 <= result <= 2
    return words[result]


async def slip39_show_checklist(
    ctx: GenericContext, step: int, backup_type: BackupType
) -> None:
    from trezor.enums import BackupType

    assert backup_type in (BackupType.Slip39_Basic, BackupType.Slip39_Advanced)

    items = (
        (
            "Number of shares",
            "Set threshold",
            "Write down and check all shares",
        )
        if backup_type == BackupType.Slip39_Basic
        else (
            "Number of groups",
            "Number of shares",
            "Set sizes and thresholds",
        )
    )

    result = await interact(
        ctx,
        RustLayout(
            trezorui2.show_checklist(
                title="BACKUP CHECKLIST",
                button="CONTINUE",
                active=step,
                items=items,
            )
        ),
        "slip39_checklist",
        ButtonRequestType.ResetDevice,
    )
    if result != CONFIRMED:
        raise ActionCancelled


async def _prompt_number(
    ctx: GenericContext,
    title: str,
    count: int,
    min_count: int,
    max_count: int,
    br_name: str,
) -> int:
    num_input = RustLayout(
        trezorui2.request_number(
            title=title.upper(),
            count=count,
            min_count=min_count,
            max_count=max_count,
        )
    )

    result = await interact(
        ctx,
        num_input,
        br_name,
        ButtonRequestType.ResetDevice,
    )

    return int(result)


async def slip39_prompt_threshold(
    ctx: GenericContext, num_of_shares: int, group_id: int | None = None
) -> int:
    await confirm_action(
        ctx,
        "slip39_prompt_threshold",
        "Threshold",
        description="= number of shares needed for recovery",
        verb="BEGIN",
        verb_cancel=None,
    )

    count = num_of_shares // 2 + 1
    # min value of share threshold is 2 unless the number of shares is 1
    # number of shares 1 is possible in advanced slip39
    min_count = min(2, num_of_shares)
    max_count = num_of_shares

    if group_id is not None:
        title = f"THRESHOLD - GROUP {group_id + 1}"
    else:
        title = "SET THRESHOLD"

    return await _prompt_number(
        ctx,
        title,
        count,
        min_count,
        max_count,
        "slip39_threshold",
    )


async def slip39_prompt_number_of_shares(
    ctx: GenericContext, group_id: int | None = None
) -> int:
    await confirm_action(
        ctx,
        "slip39_shares",
        "Number of shares",
        description="= total number of unique word lists used for wallet backup",
        verb="BEGIN",
        verb_cancel=None,
    )

    count = 5
    min_count = 1
    max_count = 16

    if group_id is not None:
        title = f"# SHARES - GROUP {group_id + 1}"
    else:
        title = "NUMBER OF SHARES"

    return await _prompt_number(
        ctx,
        title,
        count,
        min_count,
        max_count,
        "slip39_shares",
    )


async def slip39_advanced_prompt_number_of_groups(ctx: GenericContext) -> int:
    count = 5
    min_count = 2
    max_count = 16

    return await _prompt_number(
        ctx,
        "NUMBER OF GROUPS",
        count,
        min_count,
        max_count,
        "slip39_groups",
    )


async def slip39_advanced_prompt_group_threshold(
    ctx: GenericContext, num_of_groups: int
) -> int:
    count = num_of_groups // 2 + 1
    min_count = 1
    max_count = num_of_groups

    return await _prompt_number(
        ctx,
        "GROUP THRESHOLD",
        count,
        min_count,
        max_count,
        "slip39_group_threshold",
    )


async def show_warning_backup(ctx: GenericContext, slip39: bool) -> None:
    await confirm_action(
        ctx,
        "backup_warning",
        "SHAMIR BACKUP" if slip39 else "WALLET BACKUP",
        description="You can use your backup to recover your wallet at any time.",
        verb="HOLD TO BEGIN",
        hold=True,
        br_code=ButtonRequestType.ResetDevice,
    )


async def show_success_backup(ctx: GenericContext) -> None:
    from . import confirm_action

    await confirm_action(
        ctx,
        "success_backup",
        "BACKUP IS DONE",
        description="Keep it safe!",
        verb="CONTINUE",
        verb_cancel=None,
        br_code=ButtonRequestType.Success,
    )
