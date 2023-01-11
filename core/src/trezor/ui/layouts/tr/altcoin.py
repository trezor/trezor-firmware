from typing import TYPE_CHECKING, Awaitable

from trezor.enums import ButtonRequestType

from . import _placeholder_confirm

if TYPE_CHECKING:
    from trezor import wire
    from typing import Sequence


async def confirm_total_ethereum(
    ctx: wire.GenericContext, total_amount: str, gas_price: str, fee_max: str
) -> Awaitable[None]:
    return await _placeholder_confirm(
        ctx,
        "confirm_total",
        "Confirm transaction",
        f"{total_amount}\nGas price:\n{gas_price}\nMaximum fee:\n{fee_max}",
        br_code=ButtonRequestType.SignTx,
    )


async def confirm_total_ripple(
    ctx: wire.GenericContext,
    address: str,
    amount: str,
) -> Awaitable[None]:
    return await _placeholder_confirm(
        ctx,
        "confirm_output",
        "Confirm sending",
        f"{amount} XRP\nto\n{address}",
        br_code=ButtonRequestType.SignTx,
    )


async def confirm_transfer_binance(
    ctx: wire.GenericContext, inputs_outputs: Sequence[tuple[str, str, str]]
) -> Awaitable[None]:
    text = ""
    for title, amount, address in inputs_outputs:
        text += f"{title}\n{amount}\nto\n{address}\n\n"
    return await _placeholder_confirm(
        ctx,
        "confirm_transfer",
        "Confirm Binance",
        text,
        br_code=ButtonRequestType.ConfirmOutput,
    )


async def confirm_decred_sstx_submission(
    ctx: wire.GenericContext,
    address: str,
    amount: str,
) -> Awaitable[None]:
    return await _placeholder_confirm(
        ctx,
        "confirm_decred_sstx_submission",
        "Purchase ticket",
        f"{amount}\nwith voting rights to\n{address}",
        br_code=ButtonRequestType.ConfirmOutput,
    )
