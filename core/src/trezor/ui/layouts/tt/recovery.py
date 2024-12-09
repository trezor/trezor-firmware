from typing import TYPE_CHECKING

import trezorui_api
from trezor import TR, ui
from trezor.enums import ButtonRequestType

from ..common import interact

if TYPE_CHECKING:
    from typing import Awaitable

    from trezor.enums import RecoveryType

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
    prompt = TR.recovery__type_word_x_of_y_template.format(word_index + 1, word_count)
    can_go_back = word_index > 0
    if is_slip39:
        keyboard = trezorui_api.request_slip39(
            prompt=prompt, prefill_word=prefill_word, can_go_back=can_go_back
        )

    else:
        keyboard = trezorui_api.request_bip39(
            prompt=prompt, prefill_word=prefill_word, can_go_back=can_go_back
        )

    word: str = await interact(
        keyboard,
        "mnemonic" if send_button_request else None,
        ButtonRequestType.MnemonicInput,
    )
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


def show_remaining_shares(
    pages: list[tuple[str, str]],
) -> Awaitable[trezorui_api.UiResult]:
    return interact(
        trezorui_api.show_remaining_shares(pages=pages),
        "show_shares",
        ButtonRequestType.Other,
    )


def show_group_share_success(
    share_index: int, group_index: int
) -> Awaitable[ui.UiResult]:
    return interact(
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


async def _confirm_abort(dry_run: bool = False) -> None:
    from . import confirm_action

    if dry_run:
        await confirm_action(
            "abort_recovery",
            TR.recovery__title_cancel_dry_run,
            TR.recovery__cancel_dry_run,
            description=TR.recovery__wanna_cancel_dry_run,
            verb=TR.buttons__cancel,
            br_code=ButtonRequestType.ProtectCall,
        )
    else:
        await confirm_action(
            "abort_recovery",
            TR.recovery__title_cancel_recovery,
            TR.recovery__progress_will_be_lost,
            TR.recovery__wanna_cancel_recovery,
            verb=TR.buttons__cancel,
            reverse=True,
            br_code=ButtonRequestType.ProtectCall,
        )


async def continue_recovery(
    button_label: str,
    text: str,
    subtext: str | None,
    recovery_type: RecoveryType,
    show_instructions: bool = False,
    remaining_shares_info: "RemainingSharesInfo | None" = None,
) -> bool:
    from trezor.enums import RecoveryType
    from trezor.wire import ActionCancelled

    if show_instructions:
        # Show this just one-time
        description = TR.recovery__enter_each_word
    else:
        description = subtext or ""

    remaining_shares = (
        format_remaining_shares_info(remaining_shares_info)
        if remaining_shares_info
        else None
    )
    homepage = trezorui_api.continue_recovery_homepage(
        text=text,
        subtext=description,
        button=button_label,
        recovery_type=recovery_type,
        remaining_shares=remaining_shares,
    )

    while True:
        result = await interact(
            homepage,
            "recovery",
            ButtonRequestType.RecoveryHomepage,
            raise_on_cancel=None,
        )

        if result is trezorui_api.CONFIRMED:
            return True
        elif result is trezorui_api.INFO and remaining_shares is not None:
            await show_remaining_shares(remaining_shares)
        else:
            try:
                await _confirm_abort(recovery_type != RecoveryType.NormalRecovery)
            except ActionCancelled:
                pass
            else:
                return False


def show_recovery_warning(
    br_name: str,
    content: str,
    subheader: str | None = None,
    button: str | None = None,
    br_code: ButtonRequestType = ButtonRequestType.Warning,
) -> Awaitable[ui.UiResult]:
    button = button or TR.buttons__try_again  # def_arg

    return interact(
        trezorui_api.show_warning(
            title=content,
            description=subheader or "",
            button=button,
            allow_cancel=False,
        ),
        br_name,
        br_code,
    )
