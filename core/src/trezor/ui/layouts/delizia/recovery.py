from typing import TYPE_CHECKING

import trezorui_api
from trezor import TR
from trezor.enums import ButtonRequestType, RecoveryType

from ..common import interact
from . import raise_if_not_confirmed

CONFIRMED = trezorui_api.CONFIRMED  # global_import_cache
CANCELLED = trezorui_api.CANCELLED  # global_import_cache
INFO = trezorui_api.INFO  # global_import_cache

if TYPE_CHECKING:
    from apps.management.recovery_device.layout import RemainingSharesInfo


async def request_word_count(recovery_type: RecoveryType) -> int:
    count = await interact(
        trezorui_api.select_word_count(recovery_type=recovery_type),
        "recovery_word_count",
        ButtonRequestType.MnemonicWordCount,
    )
    return int(count)


async def request_word(
    word_index: int,
    word_count: int,
    is_slip39: bool,
    send_button_request: bool,
    prefill_word: str = "",
) -> str:
    prompt = TR.recovery__word_x_of_y_template.format(word_index + 1, word_count)
    can_go_back = word_index > 0

    if is_slip39:
        keyboard = trezorui_api.request_slip39(
            prompt=prompt, prefill_word=prefill_word, can_go_back=can_go_back
        )
    else:
        keyboard = trezorui_api.request_bip39(
            prompt=prompt, prefill_word=prefill_word, can_go_back=can_go_back
        )

    try:
        word: str = await interact(
            keyboard,
            "mnemonic" if send_button_request else None,
            ButtonRequestType.MnemonicInput,
        )
    finally:
        keyboard.__del__()
    return word


def format_remaining_shares_info(
    remaining_shares_info: "RemainingSharesInfo",
) -> list[tuple[str, str]]:
    from trezor import strings
    from trezor.crypto.slip39 import MAX_SHARE_COUNT

    groups, shares_remaining, group_threshold = remaining_shares_info

    pages: list[tuple[str, str]] = []
    completed_groups = shares_remaining.count(0)

    for group, remaining in zip(groups, shares_remaining):
        if 0 < remaining < MAX_SHARE_COUNT:
            title = strings.format_plural(
                TR.recovery__x_more_items_starting_template_plural,
                remaining,
                TR.plurals__x_shares_needed,
            )
            words = "\n".join(group)
            pages.append((title, words))
        elif remaining == MAX_SHARE_COUNT and completed_groups < group_threshold:
            groups_remaining = group_threshold - completed_groups
            title = strings.format_plural(
                TR.recovery__x_more_items_starting_template_plural,
                groups_remaining,
                TR.plurals__x_groups_needed,
            )
            words = "\n".join(group)
            pages.append((title, words))

    return pages


async def show_group_share_success(share_index: int, group_index: int) -> None:
    await raise_if_not_confirmed(
        trezorui_api.show_group_share_success(
            lines=[
                TR.recovery__you_have_entered,
                TR.recovery__share_num_template.format(share_index + 1),
                TR.words__from,
                TR.recovery__group_num_template.format(group_index + 1),
            ],
        ),
        "share_success",
        ButtonRequestType.Other,
    )


async def continue_recovery(
    _button_label: str,  # unused on delizia
    text: str,
    subtext: str | None,
    recovery_type: RecoveryType,
    show_instructions: bool = False,
    remaining_shares_info: "RemainingSharesInfo | None" = None,
) -> bool:
    result = await interact(
        trezorui_api.continue_recovery_homepage(
            text=text,
            subtext=subtext,
            button=None,
            recovery_type=recovery_type,
            show_instructions=show_instructions,
            remaining_shares=(
                format_remaining_shares_info(remaining_shares_info)
                if remaining_shares_info
                else None
            ),
        ),
        None,
        ButtonRequestType.Other,
        raise_on_cancel=None,
    )
    return result is CONFIRMED


async def show_recovery_warning(
    br_name: str,
    content: str,
    subheader: str | None = None,
    button: str | None = None,
    br_code: ButtonRequestType = ButtonRequestType.Warning,
) -> None:
    button = button or TR.buttons__try_again  # def_arg
    await raise_if_not_confirmed(
        trezorui_api.show_warning(
            title=content or TR.words__warning,
            value=subheader or "",
            button=button,
            description="",
            danger=True,
        ),
        br_name,
        br_code,
    )
