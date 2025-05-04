from typing import Awaitable, Callable, Sequence

import trezorui_api
from trezor import TR
from trezor.enums import ButtonRequestType

from ..common import interact, raise_if_not_confirmed

CONFIRMED = trezorui_api.CONFIRMED  # global_import_cache


def show_share_words(
    share_words: Sequence[str],
    share_index: int | None = None,
    group_index: int | None = None,
) -> Awaitable[None]:
    if share_index is None:
        title = TR.reset__recovery_wallet_backup_title
    elif group_index is None:
        title = TR.reset__recovery_share_title_template.format(share_index + 1)
    else:
        title = TR.reset__group_share_title_template.format(
            group_index + 1, share_index + 1
        )

    return raise_if_not_confirmed(
        trezorui_api.show_share_words(
            words=share_words,
            title=title,
        ),
        "backup_words",
        ButtonRequestType.ResetDevice,
    )


async def select_word(
    words: Sequence[str],
    share_index: int | None,
    checked_index: int,
    count: int,
    group_index: int | None = None,
) -> str:
    if share_index is None:
        title: str = TR.reset__check_wallet_backup_title
    elif group_index is None:
        title = TR.reset__check_share_title_template.format(share_index + 1)
    else:
        title = TR.reset__check_group_share_title_template.format(
            group_index + 1, share_index + 1
        )

    # It may happen (with a very low probability)
    # that there will be less than three unique words to choose from.
    # In that case, duplicating the last word to make it three.
    words = list(words)
    while len(words) < 3:
        words.append(words[-1])

    result = await interact(
        trezorui_api.select_word(
            title=title,
            description=TR.reset__select_word_x_of_y_template.format(
                checked_index + 1, count
            ),
            words=(words[0], words[1], words[2]),
        ),
        None,
    )
    if __debug__ and isinstance(result, str):
        return result
    assert isinstance(result, int) and 0 <= result <= 2
    return words[result]


def slip39_show_checklist(
    step: int,
    advanced: bool,
    count: int | None = None,
    threshold: int | None = None,
) -> Awaitable[None]:
    items = (
        (
            TR.reset__slip39_checklist_set_num_shares,
            TR.reset__slip39_checklist_set_threshold,
            TR.reset__slip39_checklist_write_down,
        )
        if not advanced
        else (
            TR.reset__slip39_checklist_set_num_groups,
            TR.reset__slip39_checklist_set_num_shares,
            TR.reset__slip39_checklist_set_sizes_longer,
        )
    )

    return raise_if_not_confirmed(
        trezorui_api.show_checklist(
            title=TR.reset__slip39_checklist_title,
            button=TR.buttons__continue,
            active=step,
            items=items,
        ),
        "slip39_checklist",
        ButtonRequestType.ResetDevice,
    )


async def _prompt_number(
    title: str,
    description: Callable[[int], str],
    info: Callable[[int], str],
    count: int,
    min_count: int,
    max_count: int,
    br_name: str,
) -> int:
    num_input = trezorui_api.request_number(
        title=title,
        count=count,
        min_count=min_count,
        max_count=max_count,
        description=None,
        more_info_callback=description,
    )

    while True:
        result = await interact(
            num_input,
            br_name,
            ButtonRequestType.ResetDevice,
            raise_on_cancel=None,
        )
        if __debug__:
            if not isinstance(result, tuple):
                # DebugLink currently can't send number of shares and it doesn't
                # change the counter either so just use the initial value.
                result = result, count
        status, value = result

        if status == CONFIRMED:
            assert isinstance(value, int)
            return value

        await interact(
            trezorui_api.show_simple(
                title=None,
                text=info(value),
                button=TR.buttons__ok_i_understand,
            ),
            None,
            raise_on_cancel=None,
        )


def slip39_prompt_threshold(
    num_of_shares: int, group_id: int | None = None
) -> Awaitable[int]:
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

    return _prompt_number(
        TR.reset__title_set_threshold,
        description,
        info,
        count,
        min_count,
        max_count,
        "slip39_threshold",
    )


def slip39_prompt_number_of_shares(
    num_words: int, group_id: int | None = None
) -> Awaitable[int]:
    count = 5
    min_count = 1
    max_count = 16

    def description(i: int) -> str:
        if group_id is None:
            if i == 1:
                return TR.reset__only_one_share_will_be_created
            else:
                return TR.reset__num_of_share_holders_template.format(i)
        else:
            return TR.reset__total_number_of_shares_in_group_template.format(
                group_id + 1
            )

    if group_id is None:
        info = TR.reset__num_of_shares_basic_info_template.format(num_words)
    else:
        info = TR.reset__num_of_shares_advanced_info_template.format(
            num_words, group_id + 1
        )

    return _prompt_number(
        TR.reset__title_set_number_of_shares,
        description,
        lambda i: info,
        count,
        min_count,
        max_count,
        "slip39_shares",
    )


def slip39_advanced_prompt_number_of_groups() -> Awaitable[int]:
    count = 5
    min_count = 2
    max_count = 16
    description = TR.reset__group_description
    info = TR.reset__group_info

    return _prompt_number(
        TR.reset__title_set_number_of_groups,
        lambda i: description,
        lambda i: info,
        count,
        min_count,
        max_count,
        "slip39_groups",
    )


def slip39_advanced_prompt_group_threshold(num_of_groups: int) -> Awaitable[int]:
    count = num_of_groups // 2 + 1
    min_count = 1
    max_count = num_of_groups
    description = TR.reset__required_number_of_groups
    info = TR.reset__advanced_group_threshold_info

    return _prompt_number(
        TR.reset__title_set_group_threshold,
        lambda i: description,
        lambda i: info,
        count,
        min_count,
        max_count,
        "slip39_group_threshold",
    )


def show_intro_backup(single_share: bool, num_of_words: int | None) -> Awaitable[None]:
    if single_share:
        assert num_of_words is not None
        description = TR.backup__info_single_share_backup.format(num_of_words)
    else:
        description = TR.backup__info_multi_share_backup

    return raise_if_not_confirmed(
        trezorui_api.show_info(
            title="",
            description=description,
            button=TR.buttons__continue,
        ),
        "backup_intro",
        ButtonRequestType.ResetDevice,
    )


def show_warning_backup() -> Awaitable[trezorui_api.UiResult]:
    return interact(
        trezorui_api.show_info(
            title=TR.reset__never_make_digital_copy,
            description="",
            button=TR.buttons__ok_i_understand,
        ),
        "backup_warning",
        ButtonRequestType.ResetDevice,
    )


async def show_success_backup() -> None:
    from . import show_success

    await show_success(
        "success_backup",
        TR.reset__use_your_backup,
        TR.reset__your_backup_is_done,
    )


def show_reset_warning(
    br_name: str,
    content: str,
    subheader: str | None = None,
    button: str | None = None,
    br_code: ButtonRequestType = ButtonRequestType.Warning,
) -> Awaitable[trezorui_api.UiResult]:
    button = button or TR.buttons__try_again  # def_arg
    return interact(
        trezorui_api.show_warning(
            title=subheader or "",
            description=content,
            button=button,
            allow_cancel=False,
        ),
        br_name,
        br_code,
    )


async def show_share_confirmation_success(
    share_index: int | None = None,
    num_of_shares: int | None = None,
    group_index: int | None = None,
) -> None:
    from . import show_success

    if share_index is None or num_of_shares is None:
        # it is a BIP39 or a 1-of-1 SLIP39 backup
        subheader = TR.reset__finished_verifying_wallet_backup
        text = ""

    elif share_index == num_of_shares - 1:
        if group_index is None:
            subheader = TR.reset__finished_verifying_shares
        else:
            subheader = TR.reset__finished_verifying_group_template.format(
                group_index + 1
            )
        text = ""

    else:
        if group_index is None:
            subheader = TR.reset__share_checked_successfully_template.format(
                share_index + 1
            )
            text = TR.reset__continue_with_share_template.format(share_index + 2)
        else:
            subheader = TR.reset__group_share_checked_successfully_template.format(
                group_index + 1, share_index + 1
            )
            text = TR.reset__continue_with_next_share

    return await show_success("success_share_confirm", text, subheader)


async def show_share_confirmation_failure() -> None:
    await show_reset_warning(
        "warning_backup_check",
        TR.words__please_check_again,
        TR.reset__wrong_word_selected,
        TR.buttons__check_again,
        ButtonRequestType.ResetDevice,
    )
