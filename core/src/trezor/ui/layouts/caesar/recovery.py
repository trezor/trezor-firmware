from typing import TYPE_CHECKING

import trezorui_api
from trezor import TR, ui
from trezor.enums import ButtonRequestType, RecoveryType

from apps.common import backup_types

from ..common import interact
from . import show_warning

if TYPE_CHECKING:
    from typing import Awaitable, Iterable

    from apps.management.recovery_device.layout import RemainingSharesInfo


async def request_word_count(recovery_type: RecoveryType) -> int:
    count = await interact(
        trezorui_api.select_word_count(recovery_type=recovery_type),
        "recovery_word_count",
        ButtonRequestType.MnemonicWordCount,
    )
    # It can be returning a string (for example for __debug__ in tests)
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


async def show_remaining_shares(
    groups: Iterable[tuple[int, tuple[str, ...]]],  # remaining + list 3 words
    shares_remaining: list[int],
    group_threshold: int,
) -> None:
    raise NotImplementedError


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
            None,
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
    remaining_shares_info: "RemainingSharesInfo | None" = None,  # unused on caesar
) -> bool:
    # TODO: implement info_func?
    # There is very limited space on the screen
    # (and having middle button would mean shortening the right button text)

    from trezor.wire import ActionCancelled

    # Never showing info for dry-run, user already saw it and it is disturbing
    if recovery_type in (RecoveryType.DryRun, RecoveryType.UnlockRepeatedBackup):
        show_instructions = False

    if subtext:
        text += f"\n\n{subtext}"

    homepage = trezorui_api.continue_recovery_homepage(
        text=text,
        subtext=None,
        button=button_label,
        recovery_type=recovery_type,
        show_instructions=show_instructions,
        remaining_shares=None,
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

        try:
            await _confirm_abort(recovery_type != RecoveryType.NormalRecovery)
        except ActionCancelled:
            pass
        else:
            return False


async def show_invalid_mnemonic(word_count: int) -> None:
    if backup_types.is_slip39_word_count(word_count):
        await show_recovery_warning(
            "warning_invalid_share",
            TR.words__please_try_again,
            TR.recovery__invalid_share_entered,
        )
    else:
        await show_recovery_warning(
            "warning_invalid_seed",
            TR.words__please_try_again,
            TR.recovery__invalid_wallet_backup_entered,
        )


async def show_identifier_mismatch() -> None:
    await show_recovery_warning(
        "warning_mismatched_share",
        "",
        TR.recovery__share_from_another_multi_share_backup,
    )


async def show_already_added() -> None:
    await show_recovery_warning(
        "warning_known_share",
        TR.recovery__share_already_entered,
        TR.recovery__enter_different_share,
    )


async def show_group_thresholod() -> None:
    await show_recovery_warning(
        "warning_group_threshold",
        TR.recovery__group_threshold_reached,
        TR.recovery__enter_share_from_diff_group,
    )


def show_recovery_warning(
    br_name: str,
    content: str,
    subheader: str | None = None,
    button: str | None = None,
    br_code: ButtonRequestType = ButtonRequestType.Warning,
) -> Awaitable[ui.UiResult]:
    button = button or TR.buttons__try_again  # def_arg
    return show_warning(br_name, content, subheader, button, br_code=br_code)


async def show_dry_run_result(result: bool, is_slip39: bool) -> None:
    from trezor.ui.layouts import show_success

    if result:
        if is_slip39:
            text = TR.recovery__dry_run_slip39_valid_match
        else:
            text = TR.recovery__dry_run_bip39_valid_match
        await show_success("success_dry_recovery", text, button=TR.buttons__continue)
    else:
        if is_slip39:
            text = TR.recovery__dry_run_slip39_valid_mismatch
        else:
            text = TR.recovery__dry_run_bip39_valid_mismatch
        await show_recovery_warning(
            "warning_dry_recovery", "", text, button=TR.buttons__continue
        )
