from typing import TYPE_CHECKING

import trezor.ui.layouts as layouts
from trezor import TR, strings

from . import consts

if TYPE_CHECKING:
    from trezor.messages import TronTransferContract


def format_trx_amount(amount: int) -> str:
    return f"{strings.format_amount(amount, consts.TRX_AMOUNT_DECIMALS)} TRX"


async def confirm_transfer_contract(msg: TronTransferContract) -> None:
    await layouts.confirm_address(TR.send__send_from, msg.owner_address, chunkify=True)
    await layouts.confirm_output(
        msg.to_address,
        format_trx_amount(msg.amount),
        chunkify=True,
    )
