from typing import TYPE_CHECKING

import trezorui2
from trezor import TR, ui
from trezor.enums import ButtonRequestType, RecoveryType

from ..common import interact
from . import show_warning

if TYPE_CHECKING:
    from typing import Awaitable, Iterable

    from apps.management.recovery_device.layout import RemainingSharesInfo


async def request_word_count(recovery_type: RecoveryType) -> int:
    count = await interact(
        trezorui2.select_word_count(recovery_type=recovery_type),
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
        keyboard = trezorui2.request_slip39(
            prompt=prompt, prefill_word=prefill_word, can_go_back=can_go_back
        )

    else:
        keyboard = trezorui2.request_bip39(
            prompt=prompt, prefill_word=prefill_word, can_go_back=can_go_back
        )

    word: str = await interact(
        keyboard,
        "mnemonic" if send_button_request else None,
        ButtonRequestType.MnemonicInput,
    )
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
        trezorui2.show_group_share_success(
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
    remaining_shares_info: "RemainingSharesInfo | None" = None,  # unused on TR
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

    homepage = trezorui2.confirm_recovery(
        title="",
        description=text,
        button=button_label,
        recovery_type=recovery_type,
        info_button=False,
        show_instructions=show_instructions,
    )
    while True:
        result = await interact(
            homepage,
            "recovery",
            ButtonRequestType.RecoveryHomepage,
            raise_on_cancel=None,
        )
        if result is trezorui2.CONFIRMED:
            return True

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
    return show_warning(br_name, content, subheader, button, br_code=br_code)
