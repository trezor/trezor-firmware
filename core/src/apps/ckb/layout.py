"""CKB transaction signing UI layouts."""

from trezor import TR
from trezor.strings import format_amount, format_amount_unit
from trezor.ui.layouts import confirm_output, confirm_total, show_warning

DECIMALS = 8


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


async def require_confirm_total(total: int, fee: int) -> None:
    await confirm_total(
        _format_ckb_amount(total),
        _format_ckb_amount(fee),
        title=TR.words__title_summary,
    )
