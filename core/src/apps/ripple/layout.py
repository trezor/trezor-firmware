from trezor.enums import ButtonRequestType
from trezor.strings import format_amount
from trezor.ui.layouts import confirm_metadata, confirm_total

from .helpers import DECIMALS


async def require_confirm_total(total: int, fee: int) -> None:
    await confirm_total(
        format_amount(total, DECIMALS) + " XRP",
        format_amount(fee, DECIMALS) + " XRP",
    )


async def require_confirm_destination_tag(tag: int) -> None:
    await confirm_metadata(
        "confirm_destination_tag",
        "Confirm tag",
        "Destination tag:\n{}",
        str(tag),
        ButtonRequestType.ConfirmOutput,
    )


async def require_confirm_tx(to: str, value: int, chunkify: bool = False) -> None:
    from trezor.ui.layouts import confirm_output

    await confirm_output(to, format_amount(value, DECIMALS) + " XRP", chunkify=chunkify)
