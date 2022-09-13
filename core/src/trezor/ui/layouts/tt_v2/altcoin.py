from typing import TYPE_CHECKING

from trezor import wire
from trezor.enums import ButtonRequestType
from trezor.ui.layouts import (
    confirm_amount,
    confirm_blob,
    confirm_output,
    confirm_total,
)

if TYPE_CHECKING:
    from typing import Sequence

    pass


async def confirm_total_ethereum(
    ctx: wire.GenericContext, total_amount: str, gas_price: str, fee_max: str
) -> None:
    await confirm_amount(
        ctx,
        title="Confirm fee",
        description="Gas price:",
        amount=gas_price,
    )
    await confirm_total(
        ctx,
        total_amount=total_amount,
        fee_amount=fee_max,
        total_label="Amount sent:",
        fee_label="Maximum fee:",
    )


async def confirm_total_ripple(
    ctx: wire.GenericContext,
    address: str,
    amount: str,
) -> None:
    await confirm_output(ctx, address, amount + " XRP")


async def confirm_transfer_binance(
    ctx: wire.GenericContext, inputs_outputs: Sequence[tuple[str, str, str]]
) -> None:
    for title, amount, address in inputs_outputs:
        await confirm_blob(
            ctx,
            "confirm_transfer",
            title,
            f"{amount}\nto\n{address}",
            br_code=ButtonRequestType.ConfirmOutput,
        )


async def confirm_decred_sstx_submission(
    ctx: wire.GenericContext,
    address: str,
    amount: str,
) -> None:
    await confirm_blob(
        ctx,
        "confirm_decred_sstx_submission",
        "Purchase ticket",
        f"{amount}\nwith voting rights to\n{address}",
        br_code=ButtonRequestType.ConfirmOutput,
    )
