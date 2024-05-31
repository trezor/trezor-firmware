from typing import TYPE_CHECKING

import trezorui2
from trezor import TR
from trezor.enums import ButtonRequestType
from trezor.wire import ActionCancelled

from ..common import interact
from . import RustLayout, raise_if_not_confirmed

if TYPE_CHECKING:
    from typing import Callable, Sequence

    from trezor.enums import BackupType


CONFIRMED = trezorui2.CONFIRMED  # global_import_cache


async def show_share_words(
    share_words: Sequence[str],
    share_index: int | None = None,
    group_index: int | None = None,
) -> None:

    if share_index is None:
        title = TR.reset__recovery_wallet_backup_title
    elif group_index is None:
        title = TR.reset__recovery_share_title_template.format(share_index + 1)
    else:
        title = TR.reset__group_share_title_template.format(
            group_index + 1, share_index + 1
        )
    words_count = len(share_words)
    text_info = TR.reset__write_down_words_template.format(words_count)
    text_confirm = TR.reset__words_written_down_template.format(words_count)

    result = await interact(
        RustLayout(
            trezorui2.flow_show_share_words(
                title=title,
                words=share_words,
                text_info=text_info,
                text_confirm=text_confirm,
            )
        ),
        "backup_words",
        ButtonRequestType.ResetDevice,
    )

    if result != CONFIRMED:
        raise ActionCancelled


async def select_word(
    words: Sequence[str],
    share_index: int | None,
    checked_index: int,
    count: int,
    group_index: int | None = None,
) -> str:
    if share_index is None:
        description: str = TR.reset__check_wallet_backup_title
    elif group_index is None:
        description: str = TR.reset__check_share_title_template.format(share_index + 1)
    else:
        description: str = TR.reset__check_group_share_title_template.format(
            group_index + 1, share_index + 1
        )

    # It may happen (with a very low probability)
    # that there will be less than three unique words to choose from.
    # In that case, duplicating the last word to make it three.
    words = list(words)
    while len(words) < 3:
        words.append(words[-1])

    result = await RustLayout(
        trezorui2.select_word(
            title=TR.reset__select_word_x_of_y_template.format(
                checked_index + 1, count
            ),
            description=description,
            words=(words[0], words[1], words[2]),
        )
    )
    if __debug__ and isinstance(result, str):
        return result
    assert isinstance(result, int) and 0 <= result <= 2
    return words[result]


async def slip39_show_checklist(step: int, backup_type: BackupType) -> None:
    from trezor.enums import BackupType

    assert backup_type in (BackupType.Slip39_Basic, BackupType.Slip39_Advanced)

    items = (
        (
            TR.reset__slip39_checklist_set_num_shares,
            TR.reset__slip39_checklist_set_threshold,
            TR.reset__slip39_checklist_write_down_recovery,
        )
        if backup_type == BackupType.Slip39_Basic
        else (
            TR.reset__slip39_checklist_set_num_groups,
            TR.reset__slip39_checklist_set_num_shares,
            TR.reset__slip39_checklist_set_sizes_longer,
        )
    )

    result = await interact(
        RustLayout(
            trezorui2.show_checklist(
                title=TR.reset__slip39_checklist_title,
                button=TR.buttons__continue,
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
            title=title,
            description=description,
            count=count,
            min_count=min_count,
            max_count=max_count,
        )
    )

    while True:
        result = await interact(
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

        await RustLayout(
            trezorui2.show_simple(
                title=None,
                description=info(value),
                button=TR.buttons__ok_i_understand,
            )
        )
        num_input.request_complete_repaint()


async def slip39_prompt_threshold(
    num_of_shares: int, group_id: int | None = None
) -> int:
    count = num_of_shares // 2 + 1
    # min value of share threshold is 2 unless the number of shares is 1
    # number of shares 1 is possible in advanced slip39
    min_count = min(2, num_of_shares)
    max_count = num_of_shares

    def description(count: int) -> str:
        if group_id is None:
            if count == 1:
                return TR.reset__you_need_one_share
            elif count == max_count:
                return TR.reset__need_all_share_template.format(count)
            else:
                return TR.reset__need_any_share_template.format(count)
        else:
            return TR.reset__num_shares_for_group_template.format(group_id + 1)

    def info(count: int) -> str:
        # TODO: this is madness...
        text = TR.reset__the_threshold_sets_the_number_of_shares
        if group_id is None:
            text += TR.reset__needed_to_recover_your_wallet
            text += TR.reset__set_it_to_count_template.format(count)
            if num_of_shares == 1:
                text += TR.reset__one_share
            elif num_of_shares == count:
                text += TR.reset__all_x_of_y_template.format(count, num_of_shares)
            else:
                text += TR.reset__any_x_of_y_template.format(count, num_of_shares)
            text += "."
        else:
            text += TR.reset__needed_to_form_a_group
            text += TR.reset__set_it_to_count_template.format(count)
            if num_of_shares == 1:
                text += TR.reset__one_share + " "
            elif num_of_shares == count:
                text += TR.reset__all_x_of_y_template.format(count, num_of_shares)
            else:
                text += TR.reset__any_x_of_y_template.format(count, num_of_shares)
            text += " " + TR.reset__to_form_group_template.format(group_id + 1)
        return text

    return await _prompt_number(
        TR.reset__title_set_threshold,
        description,
        info,
        count,
        min_count,
        max_count,
        "slip39_threshold",
    )


async def slip39_prompt_number_of_shares(group_id: int | None = None) -> int:
    count = 5
    min_count = 1
    max_count = 16

    def description(i: int):
        if group_id is None:
            if i == 1:
                return TR.reset__only_one_share_will_be_created
            else:
                return TR.reset__num_of_shares_how_many
        else:
            return TR.reset__total_number_of_shares_in_group_template.format(
                group_id + 1
            )

    if group_id is None:
        info = TR.reset__num_of_shares_basic_info
    else:
        info = TR.reset__num_of_shares_advanced_info_template.format(group_id + 1)

    return await _prompt_number(
        TR.reset__title_set_number_of_shares,
        description,
        lambda i: info,
        count,
        min_count,
        max_count,
        "slip39_shares",
    )


async def slip39_advanced_prompt_number_of_groups() -> int:
    count = 5
    min_count = 2
    max_count = 16
    description = TR.reset__group_description
    info = TR.reset__group_info

    return await _prompt_number(
        TR.reset__title_set_number_of_groups,
        lambda i: description,
        lambda i: info,
        count,
        min_count,
        max_count,
        "slip39_groups",
    )


async def slip39_advanced_prompt_group_threshold(num_of_groups: int) -> int:
    count = num_of_groups // 2 + 1
    min_count = 1
    max_count = num_of_groups
    description = TR.reset__required_number_of_groups
    info = TR.reset__advanced_group_threshold_info

    return await _prompt_number(
        TR.reset__title_set_group_threshold,
        lambda i: description,
        lambda i: info,
        count,
        min_count,
        max_count,
        "slip39_group_threshold",
    )


async def show_warning_backup() -> None:
    result = await interact(
        RustLayout(
            trezorui2.show_warning(
                title=TR.words__important,
                value=TR.reset__never_make_digital_copy,
                button="",
                allow_cancel=False,
            )
        ),
        "backup_warning",
        ButtonRequestType.ResetDevice,
    )
    if result != CONFIRMED:
        raise ActionCancelled


async def show_success_backup() -> None:
    from . import show_success

    await show_success(
        "success_backup",
        TR.reset__use_your_backup,
        TR.reset__your_backup_is_done,
    )


async def show_reset_warning(
    br_type: str,
    content: str,
    subheader: str | None = None,
    button: str | None = None,
    br_code: ButtonRequestType = ButtonRequestType.Warning,
) -> None:
    button = button or TR.buttons__try_again  # def_arg
    await raise_if_not_confirmed(
        interact(
            RustLayout(
                trezorui2.show_warning(
                    title=subheader or "",
                    description="",
                    value=content,
                    button="",
                    allow_cancel=False,
                )
            ),
            br_type,
            br_code,
        )
    )
