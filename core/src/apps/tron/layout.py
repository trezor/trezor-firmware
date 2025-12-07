from typing import TYPE_CHECKING

import trezor.ui.layouts as layouts
from trezor import strings, TR

from . import consts

if TYPE_CHECKING:
    from trezor.messages import TronTransferContract


def format_trx_amount(amount: int) -> str:
    return f"{strings.format_amount(amount, consts.TRX_AMOUNT_DECIMALS)} TRX"


async def confirm_transfer_contract(msg: TronTransferContract) -> None:
    await layouts.confirm_address(
        TR.send__title_sending_to,
        msg.to_address,
        chunkify=True,
    )
