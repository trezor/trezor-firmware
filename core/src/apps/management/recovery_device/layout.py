from typing import TYPE_CHECKING

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
    from typing import Callable

    from trezor.enums import BackupType


async def _confirm_abort(dry_run: bool = False) -> None:
    if dry_run:
        await confirm_action(
            "abort_recovery",
            "Cancel backup check",
            description="Are you sure you want to cancel the backup check?",
            verb="CANCEL",
            br_code=ButtonRequestType.ProtectCall,
        )
    else:
        await confirm_action(
            "abort_recovery",
            "Cancel recovery",
            "All progress will be lost.",
            "Are you sure you want to cancel the recovery process?",
            verb="CANCEL",
            reverse=True,
            br_code=ButtonRequestType.ProtectCall,
        )


async def request_mnemonic(
    word_count: int, backup_type: BackupType | None
) -> str | None:
    from trezor.ui.layouts.common import button_request
    from trezor.ui.layouts.recovery import request_word

    from . import word_validity

    await button_request("mnemonic", code=ButtonRequestType.MnemonicInput)

    words: list[str] = []
    for i in range(word_count):
        word = await request_word(
            i, word_count, is_slip39=backup_types.is_slip39_word_count(word_count)
        )
        words.append(word)

        try:
            word_validity.check(backup_type, words)
        except word_validity.AlreadyAdded:
            # show_share_already_added
            await show_recovery_warning(
                "warning_known_share",
                "Share already entered",
                "Please enter a different share.",
            )
            return None
        except word_validity.IdentifierMismatch:
            # show_identifier_mismatch
            await show_recovery_warning(
                "warning_mismatched_share",
                "You have entered a share from another Shamir Backup.",
            )
            return None
        except word_validity.ThresholdReached:
            # show_group_threshold_reached
            await show_recovery_warning(
                "warning_group_threshold",
                "Group threshold reached.",
                "Enter share from a different group.",
            )
            return None

    return " ".join(words)


async def show_dry_run_result(result: bool, is_slip39: bool) -> None:
    from trezor.ui.layouts import show_success

    if result:
        if is_slip39:
            text = "The entered recovery shares are valid and match what is currently in the device."
        else:
            text = (
                "The entered recovery seed is valid and matches the one in the device."
            )
        await show_success("success_dry_recovery", text, button="Continue")
    else:
        if is_slip39:
            text = "The entered recovery shares are valid but do not match what is currently in the device."
        else:
            text = "The entered recovery seed is valid but does not match the one in the device."
        await show_recovery_warning("warning_dry_recovery", "", text, button="Continue")


async def show_invalid_mnemonic(word_count: int) -> None:
    if backup_types.is_slip39_word_count(word_count):
        await show_recovery_warning(
            "warning_invalid_share",
            "Invalid recovery share entered.",
            "Please try again",
        )
    else:
        await show_recovery_warning(
            "warning_invalid_seed",
            "Invalid recovery seed entered.",
            "Please try again",
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
