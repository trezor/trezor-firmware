from trezor import TR
from trezor.enums import ButtonRequestType
from trezor.strings import format_amount
from trezor.ui.layouts import confirm_metadata

from .helpers import NEM_MAX_DIVISIBILITY


async def require_confirm_text(action: str) -> None:
    await confirm_metadata(
        "confirm_nem",
        TR.nem__confirm_action,
        action,
        br_code=ButtonRequestType.ConfirmOutput,
    )


async def require_confirm_fee(action: str, fee: int) -> None:
    await confirm_metadata(
        "confirm_fee",
        TR.words__confirm_fee,
        action + "\n{}",
        f"{format_amount(fee, NEM_MAX_DIVISIBILITY)} XEM",
        ButtonRequestType.ConfirmOutput,
    )


async def require_confirm_content(headline: str, content: list) -> None:
    from trezor.ui.layouts import confirm_properties

    await confirm_properties(
        "confirm_content",
        headline,
        content,
    )


async def require_confirm_final(fee: int) -> None:
    # we use SignTx, not ConfirmOutput, for compatibility with T1
    await confirm_metadata(
        "confirm_final",
        TR.nem__final_confirm,
        TR.nem__sign_tx_fee_template,
        f"{format_amount(fee, NEM_MAX_DIVISIBILITY)} XEM",
        hold=True,
    )
