from typing import TYPE_CHECKING

from trezor import TR
from trezor.ui.layouts.recovery import (  # noqa: F401
    request_word_count,
    show_already_added,
    show_dry_run_result,
    show_group_share_success,
    show_group_thresholod,
    show_identifier_mismatch,
    show_recovery_warning,
)

from apps.common import backup_types

from .recover import RecoveryAborted

if TYPE_CHECKING:
    from typing import Awaitable

    from trezor.enums import BackupType

    # RemainingSharesInfo represents the data structure for remaining shares in SLIP-39 recovery:
    # - Set of tuples, each containing 2 or 3 words identifying a group
    # - List of remaining share counts for each group
    # - Group threshold (minimum number of groups required)
    RemainingSharesInfo = tuple[set[tuple[str, ...]], list[int], int]


async def request_mnemonic(
    word_count: int, backup_type: BackupType | None
) -> str | None:
    from . import word_validity

    if backup_types.is_slip39_word_count(word_count):
        title = "SLIP-39 recovery"
    else:
        title = "BIP-39 recovery"

    while True:
        mnemonic = await _recover_n4w1(title)
        if mnemonic is None:
            return None

        try:
            word_validity.check(backup_type, mnemonic.split(" "))
            return mnemonic
        except word_validity.AlreadyAdded:
            # show_share_already_added
            await show_already_added()
            return None
        except word_validity.IdentifierMismatch:
            # show_identifier_mismatch
            await show_identifier_mismatch()
            return None
        except word_validity.ThresholdReached:
            # show_group_threshold_reached
            await show_group_thresholod()
            return None


def enter_share(
    word_count: int | None = None,
    entered_remaining: tuple[int, int] | None = None,
    remaining_shares_info: RemainingSharesInfo | None = None,
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
        show_instructions,
        remaining_shares_info,
    )


async def homescreen_dialog(
    button_label: str,
    text: str,
    subtext: str | None = None,
    show_instructions: bool = False,
    remaining_shares_info: "RemainingSharesInfo | None" = None,
) -> None:
    import storage.recovery as storage_recovery
    from trezor.ui.layouts.recovery import continue_recovery

    recovery_type = storage_recovery.get_type()
    if not await continue_recovery(
        button_label,
        text,
        subtext,
        recovery_type,
        show_instructions,
        remaining_shares_info,
    ):
        raise RecoveryAborted


async def _recover_n4w1(title: str) -> str | None:
    import trezorui_api
    from trezor.ui.layouts.common import draw_simple

    from apps.debug import n4w1_mock

    with n4w1_mock.ctx as ctx:
        draw_simple(
            trezorui_api.show_simple(
                title=title,
                text="Tap your N4W1 to recover",
            )
        )
        blob = await ctx.read(key="mnemonic")
        if blob is None:
            return blob
        # TODO: use protobuf?
        return bytes(blob).decode()
