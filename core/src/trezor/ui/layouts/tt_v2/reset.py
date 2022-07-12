from typing import TYPE_CHECKING

from trezor import wire
from trezor.enums import BackupType, ButtonRequestType

import trezorui2

from ..common import interact
from . import _RustLayout

if TYPE_CHECKING:
    from typing import Callable, Sequence, List

    pass


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
    ctx: wire.GenericContext,
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
    #     _RustLayout(
    #         trezorui2.show_simple(
    #             title=title,
    #             description=f"Write down these {len(share_words)} words in the exact order:",
    #             button="SHOW WORDS",
    #         ),
    #     ),
    #     "confirm_backup_words",
    #     ButtonRequestType.ResetDevice,
    # )
    # if result != trezorui2.CONFIRMED:
    #     raise wire.ActionCancelled

    pages = _split_share_into_pages(share_words)

    result = await interact(
        ctx,
        _RustLayout(
            trezorui2.show_share_words(
                title=title,
                pages=pages,
            ),
            is_backup=True,
        ),
        "backup_words",
        ButtonRequestType.ResetDevice,
    )
    if result != trezorui2.CONFIRMED:
        raise wire.ActionCancelled


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
        _RustLayout(
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
    ctx: wire.GenericContext, step: int, backup_type: BackupType
) -> None:
    items = []
    if backup_type is BackupType.Slip39_Basic:
        items.append("Set number of shares")
        items.append("Set threshold")
        items.append("Write down and check all recovery shares")
    elif backup_type is BackupType.Slip39_Advanced:
        items.append("Set number of groups")
        items.append("Set group threshold")
        items.append("Set size and threshold for each group")

    result = await interact(
        ctx,
        _RustLayout(
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
    if result != trezorui2.CONFIRMED:
        raise wire.ActionCancelled


async def _prompt_number(
    ctx: wire.GenericContext,
    title: str,
    description: Callable[[int], str],
    info: Callable[[int], str],
    count: int,
    min_count: int,
    max_count: int,
    br_name: str,
) -> int:
    num_input = _RustLayout(
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

        if status == trezorui2.CONFIRMED:
            assert isinstance(value, int)
            return value

        await ctx.wait(
            _RustLayout(
                trezorui2.show_simple(
                    title=None, description=info(value), button="OK, I UNDERSTAND"
                )
            )
        )
        num_input.request_complete_repaint()


async def slip39_prompt_threshold(
    ctx: wire.GenericContext, num_of_shares: int, group_id: int | None = None
) -> int:
    count = num_of_shares // 2 + 1
    # min value of share threshold is 2 unless the number of shares is 1
    # number of shares 1 is possible in advanced slip39
    min_count = min(2, num_of_shares)
    max_count = num_of_shares

    def description(count: int):
        if group_id is None:
            if count == 1:
                return "For recovery you need 1 share."
            elif count == max_count:
                return f"For recovery you need all {count} of the shares."
            else:
                return f"For recovery you need any {count} of the shares."
        else:
            return f"The required number of shares to form Group {group_id + 1}."

    def info(count: int):
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
        title="SET THRESHOLD",
        description=description,
        info=info,
        count=count,
        min_count=min_count,
        max_count=max_count,
        br_name="slip39_threshold",
    )


async def slip39_prompt_number_of_shares(
    ctx: wire.GenericContext, group_id: int | None = None
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
        title="SET NUMBER OF SHARES",
        description=description,
        info=lambda i: info,
        count=count,
        min_count=min_count,
        max_count=max_count,
        br_name="slip39_shares",
    )


async def slip39_advanced_prompt_number_of_groups(ctx: wire.GenericContext) -> int:
    count = 5
    min_count = 2
    max_count = 16
    description = "A group is made up of recovery shares."
    info = "Each group has a set number of shares and its own threshold. In the next steps you will set the numbers of shares and the thresholds."

    return await _prompt_number(
        ctx,
        title="SET NUMBER OF GROUPS",
        description=lambda i: description,
        info=lambda i: info,
        count=count,
        min_count=min_count,
        max_count=max_count,
        br_name="slip39_groups",
    )


async def slip39_advanced_prompt_group_threshold(
    ctx: wire.GenericContext, num_of_groups: int
) -> int:
    count = num_of_groups // 2 + 1
    min_count = 1
    max_count = num_of_groups
    description = "The required number of groups for recovery."
    info = "The group threshold specifies the number of groups required to recover your wallet."

    return await _prompt_number(
        ctx,
        title="SET GROUP THRESHOLD",
        description=lambda i: description,
        info=lambda i: info,
        count=count,
        min_count=min_count,
        max_count=max_count,
        br_name="slip39_group_threshold",
    )


async def show_warning_backup(ctx: wire.GenericContext, slip39: bool) -> None:
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
        _RustLayout(
            trezorui2.show_info(
                title=description,
                button="OK, I UNDERSTAND",
                allow_cancel=False,
            )
        ),
        "backup_warning",
        ButtonRequestType.ResetDevice,
    )
    if result != trezorui2.CONFIRMED:
        raise wire.ActionCancelled
