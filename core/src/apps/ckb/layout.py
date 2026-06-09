"""CKB transaction signing UI layouts."""

from trezor import TR
from trezor.strings import format_amount, format_amount_unit
from trezor.ui.layouts import confirm_output, confirm_total, show_warning

DECIMALS = 8

# Warn when the fee exceeds this fraction of the total output value. CKB has no
# per-byte fee table on the device, so a proportional rule flags an unusually
# large fee while leaving normal fees unprompted.
FEE_WARNING_NUMERATOR = 1
FEE_WARNING_DENOMINATOR = 10  # 10 %


def _format_ckb_amount(shannons: int) -> str:
    return format_amount_unit(format_amount(shannons, DECIMALS), "CKB")


async def require_confirm_testnet() -> None:
    await show_warning(
        "ckb_testnet",
        "You are signing a testnet transaction.",
    )


async def require_confirm_type_script() -> None:
    await show_warning(
        "ckb_type_script",
        "This output has a type script. Funds may be restricted.",
    )


async def require_confirm_output(
    address: str, amount: int, chunkify: bool = False
) -> None:
    await confirm_output(
        address,
        _format_ckb_amount(amount),
        title=TR.send__confirm_sending,
        chunkify=chunkify,
    )


def fee_over_threshold(fee: int, total_out: int) -> bool:
    """Whether the fee is large enough relative to the total output value to warn."""
    return fee * FEE_WARNING_DENOMINATOR > total_out * FEE_WARNING_NUMERATOR


async def require_confirm_fee_over_threshold(fee: int, total_out: int) -> None:
    if fee_over_threshold(fee, total_out):
        await show_warning(
            "ckb_fee_over_threshold",
            "The fee is unusually high.",
            _format_ckb_amount(fee),
        )


async def require_confirm_total(total: int, fee: int) -> None:
    await confirm_total(
        _format_ckb_amount(total),
        _format_ckb_amount(fee),
        title=TR.words__title_summary,
    )
