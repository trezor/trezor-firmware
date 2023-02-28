from typing import TYPE_CHECKING

from trezor.enums import ButtonRequestType
from trezor.wire import ActionCancelled

import trezorui2

from ..common import interact
from . import RustLayout

if TYPE_CHECKING:
    from typing import Callable, Sequence, List
    from trezor.enums import BackupType
    from trezor.wire import GenericContext


CONFIRMED = trezorui2.CONFIRMED  # global_import_cache


def _split_share_into_pages(share_words: Sequence[str], per_page: int = 4) -> List[str]:
    pages = []
    current = ""

    for i, word in enumerate(share_words):
        if i % per_page == 0:
            if i != 0:
                pages.append(current)
            current = ""
        else:
            current += "\n"
        current += f"{i + 1}. {word}"

    if current:
        pages.append(current)

    return pages


async def show_share_words(
    ctx: GenericContext,
    share_words: Sequence[str],
    share_index: int | None = None,
    group_index: int | None = None,
) -> None:
    if share_index is None:
        title = "RECOVERY SEED"
    elif group_index is None:
        title = f"RECOVERY SHARE #{share_index + 1}"
    else:
        title = f"GROUP {group_index + 1} - SHARE {share_index + 1}"

    # result = await interact(
    #     ctx,
    #     RustLayout(
    #         trezorui2.show_simple(
    #             title=title,
    #             description=f"Write down these {len(share_words)} words in the exact order:",
    #             button="SHOW WORDS",
    #         ),
    #     ),
    #     "confirm_backup_words",
    #     ButtonRequestType.ResetDevice,
    # )
    # if result != CONFIRMED:
    #     raise ActionCancelled

    pages = _split_share_into_pages(share_words)

    result = await interact(
        ctx,
        RustLayout(
            trezorui2.show_share_words(
                title=title,
                pages=pages,
            ),
            is_backup=True,
        ),
        "backup_words",
        ButtonRequestType.ResetDevice,
    )
    if result != CONFIRMED:
        raise ActionCancelled


async def select_word(
    ctx: GenericContext,
    words: Sequence[str],
    share_index: int | None,
    checked_index: int,
    count: int,
    group_index: int | None = None,
) -> str:
    if share_index is None:
        title: str = "CHECK SEED"
    elif group_index is None:
        title = f"CHECK SHARE #{share_index + 1}"
    else:
        title = f"CHECK G{group_index + 1} - SHARE {share_index + 1}"

    # It may happen (with a very low probability)
    # that there will be less than three unique words to choose from.
    # In that case, duplicating the last word to make it three.
    words = list(words)
    while len(words) < 3:
        words.append(words[-1])

    result = await ctx.wait(
        RustLayout(
            trezorui2.select_word(
                title=title,
                description=f"Select word {checked_index + 1} of {count}:",
                words=(words[0].upper(), words[1].upper(), words[2].upper()),
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
            "Set number of shares",
            "Set threshold",
            "Write down and check all recovery shares",
        )
        if backup_type == BackupType.Slip39_Basic
        else (
            "Set number of groups",
            "Set number of shares",
            "Set size and threshold for each group",
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
    description: Callable[[int], str],
    info: Callable[[int], str],
    count: int,
    min_count: int,
    max_count: int,
    br_name: str,
) -> int:
    num_input = RustLayout(
        trezorui2.request_number(
            title=title.upper(),
            description=description,
            count=count,
            min_count=min_count,
            max_count=max_count,
        )
    )

    while True:
        result = await interact(
            ctx,
            num_input,
            br_name,
            ButtonRequestType.ResetDevice,
        )
        if __debug__:
            if not isinstance(result, tuple):
                # DebugLink currently can't send number of shares and it doesn't
                # change the counter either so just use the initial value.
                result = (result, count)
        status, value = result

        if status == CONFIRMED:
            assert isinstance(value, int)
            return value

        await ctx.wait(
            RustLayout(
                trezorui2.show_simple(
                    title=None, description=info(value), button="OK, I UNDERSTAND"
                )
            )
        )
        num_input.request_complete_repaint()


async def slip39_prompt_threshold(
    ctx: GenericContext, num_of_shares: int, group_id: int | None = None
) -> int:
    count = num_of_shares // 2 + 1
    # min value of share threshold is 2 unless the number of shares is 1
    # number of shares 1 is possible in advanced slip39
    min_count = min(2, num_of_shares)
    max_count = num_of_shares

    def description(count: int) -> str:
        if group_id is None:
            if count == 1:
                return "For recovery you need 1 share."
            elif count == max_count:
                return f"For recovery you need all {count} of the shares."
            else:
                return f"For recovery you need any {count} of the shares."
        else:
            return f"The required number of shares to form Group {group_id + 1}."

    def info(count: int) -> str:
        text = "The threshold sets the number of shares "
        if group_id is None:
            text += "needed to recover your wallet. "
            text += f"Set it to {count} and you will need "
            if num_of_shares == 1:
                text += "1 share."
            elif num_of_shares == count:
                text += f"all {count} of your {num_of_shares} shares."
            else:
                text += f"any {count} of your {num_of_shares} shares."
        else:
            text += "needed to form a group. "
            text += f"Set it to {count} and you will "
            if num_of_shares == 1:
                text += "need 1 share "
            elif num_of_shares == count:
                text += f"need all {count} of {num_of_shares} shares "
            else:
                text += f"need any {count} of {num_of_shares} shares "
            text += f"to form Group {group_id + 1}."
        return text

    return await _prompt_number(
        ctx,
        "SET THRESHOLD",
        description,
        info,
        count,
        min_count,
        max_count,
        "slip39_threshold",
    )


async def slip39_prompt_number_of_shares(
    ctx: GenericContext, group_id: int | None = None
) -> int:
    count = 5
    min_count = 1
    max_count = 16

    def description(i: int):
        if group_id is None:
            if i == 1:
                return "Only one share will be created."
            else:
                return f"{i} people or locations will each hold one share."
        else:
            return f"Set the total number of shares in Group {group_id + 1}."

    if group_id is None:
        info = "Each recovery share is a sequence of 20 words. Next you will choose how many shares you need to recover your wallet."
    else:
        info = f"Each recovery share is a sequence of 20 words. Next you will choose the threshold number of shares needed to form Group {group_id + 1}."

    return await _prompt_number(
        ctx,
        "SET NUMBER OF SHARES",
        description,
        lambda i: info,
        count,
        min_count,
        max_count,
        "slip39_shares",
    )


async def slip39_advanced_prompt_number_of_groups(ctx: GenericContext) -> int:
    count = 5
    min_count = 2
    max_count = 16
    description = "A group is made up of recovery shares."
    info = "Each group has a set number of shares and its own threshold. In the next steps you will set the numbers of shares and the thresholds."

    return await _prompt_number(
        ctx,
        "SET NUMBER OF GROUPS",
        lambda i: description,
        lambda i: info,
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
    description = "The required number of groups for recovery."
    info = "The group threshold specifies the number of groups required to recover your wallet."

    return await _prompt_number(
        ctx,
        "SET GROUP THRESHOLD",
        lambda i: description,
        lambda i: info,
        count,
        min_count,
        max_count,
        "slip39_group_threshold",
    )


async def show_warning_backup(ctx: GenericContext, slip39: bool) -> None:
    if slip39:
        description = (
            "Never make a digital copy of your shares and never upload them online."
        )
    else:
        description = (
            "Never make a digital copy of your seed and never upload it online."
        )
    result = await interact(
        ctx,
        RustLayout(
            trezorui2.show_info(
                title=description,
                button="OK, I UNDERSTAND",
                allow_cancel=False,
            )
        ),
        "backup_warning",
        ButtonRequestType.ResetDevice,
    )
    if result != CONFIRMED:
        raise ActionCancelled
