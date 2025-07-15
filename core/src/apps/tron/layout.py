from typing import TYPE_CHECKING

import trezor.ui.layouts as layouts
from trezor import TR, strings

from . import consts

if TYPE_CHECKING:
    from trezor.messages import TronTransferContract


def format_trx_amount(amount: int) -> str:
    return f"{strings.format_amount(amount, consts.TRX_AMOUNT_DECIMALS)} TRX"


async def confirm_transfer_contract(
    msg: TronTransferContract, trezor_account: str
) -> None:
    if trezor_account != msg.owner_address:
        # If the owner address is not the same as the Trezor account, we need to confirm the owner address.
        # This may occur in scenarios involving multi-signatures.
        # The `confirm_output` has a `source_account` field, but it does not work in T3B1; perhaps we should unify them.
        await layouts.confirm_address(
            TR.send__send_from, msg.owner_address, chunkify=False
        )
    await layouts.confirm_output(
        msg.to_address,
        format_trx_amount(msg.amount),
    )
