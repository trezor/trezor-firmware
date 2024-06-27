from typing import TYPE_CHECKING

from trezor import TR
from trezor.enums import ButtonRequestType
from trezor.ui.layouts.recovery import (  # noqa: F401
    request_word_count,
    show_group_share_success,
    show_recovery_warning,
    show_remaining_shares,
)

from apps.common import backup_types

if TYPE_CHECKING:
    from typing import Callable

    from trezor.enums import BackupType


async def request_mnemonic(
    word_count: int, backup_type: BackupType | None
) -> str | None:
    from trezor.ui.layouts.common import button_request
    from trezor.ui.layouts.recovery import request_word

    from . import word_validity

    await button_request("mnemonic", code=ButtonRequestType.MnemonicInput)

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
            prefill_word=words[i],
        )

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
                "",
                TR.recovery__share_from_another_multi_share_backup,
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
            TR.words__please_try_again,
            TR.recovery__invalid_share_entered,
        )
    else:
        await show_recovery_warning(
            "warning_invalid_seed",
            TR.words__please_try_again,
            TR.recovery__invalid_wallet_backup_entered,
        )


async def homescreen_dialog(
    button_label: str,
    text: str,
    subtext: str | None = None,
    info_func: Callable | None = None,
    show_info: bool = False,
) -> None:
    import storage.recovery as storage_recovery
    from trezor.ui.layouts.recovery import continue_recovery

    from .recover import RecoveryAborted

    recovery_type = storage_recovery.get_type()
    if not await continue_recovery(
        button_label, text, subtext, info_func, recovery_type, show_info
    ):
        raise RecoveryAborted
