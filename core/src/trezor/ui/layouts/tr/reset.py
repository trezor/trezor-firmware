from typing import TYPE_CHECKING

import trezorui2
from trezor import TR
from trezor.enums import ButtonRequestType
from trezor.wire import ActionCancelled

from ..common import interact
from . import RustLayout, confirm_action, show_warning

CONFIRMED = trezorui2.CONFIRMED  # global_import_cache

if TYPE_CHECKING:
    from typing import Sequence

    from trezor.enums import BackupType


async def show_share_words(
    share_words: Sequence[str],
    share_index: int | None = None,
    group_index: int | None = None,
) -> None:
    # Showing words, asking for write down confirmation and preparing for check
    br_type = "backup_words"
    br_code = ButtonRequestType.ResetDevice

    if share_index is None:
        title = TR.reset__share_words_title
        check_title = TR.reset__check_backup_title
    elif group_index is None:
        title = f"{TR.words__title_share} #{share_index + 1}"
        check_title = (
            f"{TR.words__title_check} {TR.words__title_share} #{share_index + 1}"
        )
    else:
        title = f"{TR.words__title_group} {group_index + 1} - {TR.words__title_share} {share_index + 1}"
        check_title = f"{TR.words__title_group} {group_index + 1} - {TR.words__title_share} {share_index + 1}"

    # We want the option to go back from words to the previous screen
    # (by sending CANCELLED)
    while True:
        await confirm_action(
            br_type,
            title,
            description=TR.reset__write_down_words_template.format(len(share_words)),
            verb=TR.buttons__show_words,
            verb_cancel=None,
            br_code=br_code,
        )

        result = await interact(
            RustLayout(
                trezorui2.show_share_words(  # type: ignore [Arguments missing for parameters]
                    share_words=share_words,  # type: ignore [No parameter named "share_words"]
                )
            ),
            br_type,
            br_code,
        )
        if result is CONFIRMED:
            break

    await confirm_action(
        br_type,
        check_title,
        description=TR.reset__select_correct_word,
        verb=TR.buttons__continue,
        verb_cancel=None,
        br_code=br_code,
    )


async def select_word(
    words: Sequence[str],
    share_index: int | None,
    checked_index: int,
    count: int,
    group_index: int | None = None,
) -> str:
    from trezor.strings import format_ordinal
    from trezor.wire.context import wait

    # It may happen (with a very low probability)
    # that there will be less than three unique words to choose from.
    # In that case, duplicating the last word to make it three.
    words = list(words)
    while len(words) < 3:
        words.append(words[-1])

    word_ordinal = format_ordinal(checked_index + 1).upper()
    result = await wait(
        RustLayout(
            trezorui2.select_word(
                title="",
                description=TR.reset__select_word_template.format(word_ordinal),
                words=(words[0].lower(), words[1].lower(), words[2].lower()),
            )
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
            TR.reset__slip39_checklist_num_shares,
            TR.reset__slip39_checklist_set_threshold,
            TR.reset__slip39_checklist_write_down,
        )
        if backup_type == BackupType.Slip39_Basic
        else (
            TR.reset__slip39_checklist_num_groups,
            TR.reset__slip39_checklist_num_shares,
            TR.reset__slip39_checklist_set_sizes,
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
    if result is not CONFIRMED:
        raise ActionCancelled


async def _prompt_number(
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
        num_input,
        br_name,
        ButtonRequestType.ResetDevice,
    )

    return int(result)


async def slip39_prompt_threshold(
    num_of_shares: int, group_id: int | None = None
) -> int:
    await confirm_action(
        "slip39_prompt_threshold",
        TR.words__title_threshold,
        description=TR.reset__threshold_info,
        verb=TR.buttons__continue,
        verb_cancel=None,
    )

    count = num_of_shares // 2 + 1
    # min value of share threshold is 2 unless the number of shares is 1
    # number of shares 1 is possible in advanced slip39
    min_count = min(2, num_of_shares)
    max_count = num_of_shares

    if group_id is not None:
        title = f"{TR.words__title_threshold} - {TR.words__title_group} {group_id + 1}"
    else:
        title = TR.words__title_threshold

    return await _prompt_number(
        title,
        count,
        min_count,
        max_count,
        "slip39_threshold",
    )


async def slip39_prompt_number_of_shares(group_id: int | None = None) -> int:
    await confirm_action(
        "slip39_shares",
        TR.reset__title_number_of_shares,
        description=TR.reset__number_of_shares_info,
        verb=TR.buttons__continue,
        verb_cancel=None,
    )

    count = 5
    min_count = 1
    max_count = 16

    if group_id is not None:
        title = f"# {TR.words__title_shares} - {TR.words__title_group} {group_id + 1}"
    else:
        title = TR.reset__title_number_of_shares

    return await _prompt_number(
        title,
        count,
        min_count,
        max_count,
        "slip39_shares",
    )


async def slip39_advanced_prompt_number_of_groups() -> int:
    count = 5
    min_count = 2
    max_count = 16

    return await _prompt_number(
        TR.reset__title_number_of_groups,
        count,
        min_count,
        max_count,
        "slip39_groups",
    )


async def slip39_advanced_prompt_group_threshold(num_of_groups: int) -> int:
    count = num_of_groups // 2 + 1
    min_count = 1
    max_count = num_of_groups

    return await _prompt_number(
        TR.reset__title_group_threshold,
        count,
        min_count,
        max_count,
        "slip39_group_threshold",
    )


async def show_warning_backup(slip39: bool) -> None:
    await show_warning(
        "backup_warning",
        TR.words__title_remember,
        TR.reset__never_make_digital_copy,
        TR.buttons__ok_i_understand,
        ButtonRequestType.ResetDevice,
    )


async def show_success_backup() -> None:
    await confirm_action(
        "success_backup",
        TR.reset__title_backup_is_done,
        description=TR.words__keep_it_safe,
        verb=TR.buttons__continue,
        verb_cancel=None,
        br_code=ButtonRequestType.Success,
    )


async def show_reset_warning(
    br_type: str,
    content: str,
    subheader: str | None = None,
    button: str | None = None,
    br_code: ButtonRequestType = ButtonRequestType.Warning,
) -> None:
    button = button or TR.buttons__try_again  # def_arg

    await show_warning(
        br_type,
        subheader or "",
        content,
        button.upper(),
        br_code=br_code,
    )
