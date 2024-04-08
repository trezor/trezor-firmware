from typing import TYPE_CHECKING

from trezor import TR
from trezor.enums import ButtonRequestType
from trezor.ui.layouts import confirm_action
from trezor.ui.layouts.recovery import (  # noqa: F401
    request_word_count,
    show_group_share_success,
    show_recovery_warning,
    show_remaining_shares,
)

from .. import backup_types

if TYPE_CHECKING:
    from typing import Awaitable, Callable

    from trezor.enums import BackupType
    from trezor.ui.layouts.common import InfoFunc


async def _confirm_abort(dry_run: bool = False) -> None:
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


async def request_mnemonic(
    word_count: int, backup_type: BackupType | None
) -> str | None:
    from trezor.ui.layouts.recovery import request_word

    from . import word_validity

    send_button_request = True

    # Allowing to go back to previous words, therefore cannot use just loop over range(word_count)
    words: list[str] = [""] * word_count
    i = 0
    while True:
        # All the words have been entered
        if i >= word_count:
            break

        # Prefilling the previously inputted word in case of going back
        word = await request_word(
            i,
            word_count,
            is_slip39=backup_types.is_slip39_word_count(word_count),
            send_button_request=send_button_request,
            prefill_word=words[i],
        )
        send_button_request = False

        # User has decided to go back
        if not word:
            if i > 0:
                i -= 1
            continue

        words[i] = word

        i += 1

        try:
            non_empty_words = [word for word in words if word]
            word_validity.check(backup_type, non_empty_words)
        except word_validity.AlreadyAdded:
            # show_share_already_added
            await show_recovery_warning(
                "warning_known_share",
                TR.recovery__share_already_entered,
                TR.recovery__enter_different_share,
            )
            return None
        except word_validity.IdentifierMismatch:
            # show_identifier_mismatch
            await show_recovery_warning(
                "warning_mismatched_share",
                TR.recovery__share_from_another_shamir,
            )
            return None
        except word_validity.ThresholdReached:
            # show_group_threshold_reached
            await show_recovery_warning(
                "warning_group_threshold",
                TR.recovery__group_threshold_reached,
                TR.recovery__enter_share_from_diff_group,
            )
            return None

    return " ".join(words)


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


async def show_invalid_mnemonic(word_count: int) -> None:
    if backup_types.is_slip39_word_count(word_count):
        await show_recovery_warning(
            "warning_invalid_share",
            TR.recovery__invalid_share_entered,
            TR.words__please_try_again,
        )
    else:
        await show_recovery_warning(
            "warning_invalid_seed",
            TR.recovery__invalid_seed_entered,
            TR.words__please_try_again,
        )


def enter_share(
    word_count: int | None = None,
    entered_remaining: tuple[int, int] | None = None,
    info_func: Callable | None = None,
) -> Awaitable[None]:
    from trezor import strings

    show_instructions = False

    if word_count is not None:
        # First-time entry. Show instructions and word count.
        text = TR.recovery__enter_any_share
        subtext = TR.recovery__word_count_template.format(word_count)
        show_instructions = True

    elif entered_remaining is not None:
        # Basic Shamir. There is only one group, we report entered/remaining count.
        entered, remaining = entered_remaining
        total = entered + remaining
        text = TR.recovery__x_of_y_entered_template.format(entered, total)
        subtext = strings.format_plural(
            TR.recovery__x_more_shares_needed_template_plural,
            remaining,
            TR.plurals__x_shares_needed,
        )

    else:
        # SuperShamir. We cannot easily show entered/remaining across groups,
        # the caller provided an info_func that has the details.
        text = TR.recovery__more_shares_needed
        subtext = None

    return homescreen_dialog(
        TR.buttons__enter_share,
        text,
        subtext,
        info_func,
        show_instructions,
    )


async def homescreen_dialog(
    button_label: str,
    text: str,
    subtext: str | None = None,
    info_func: InfoFunc | None = None,
    show_info: bool = False,
) -> None:
    import storage.recovery as storage_recovery
    from trezor.ui.layouts.recovery import continue_recovery
    from trezor.wire import ActionCancelled

    from .recover import RecoveryAborted

    while True:
        dry_run = storage_recovery.is_dry_run()
        if await continue_recovery(
            button_label, text, subtext, info_func, dry_run, show_info
        ):
            # go forward in the recovery process
            break
        # user has chosen to abort, confirm the choice
        try:
            await _confirm_abort(dry_run)
        except ActionCancelled:
            pass
        else:
            raise RecoveryAborted
