from micropython import const
from typing import TYPE_CHECKING

import trezor.ui.layouts as layouts
from trezor import TR, strings
from trezor.crypto import base58

if TYPE_CHECKING:
    from trezor.messages import TronTransferContract


def format_trx_amount(amount: int) -> str:
    # 1 SUN = 0.000001 TRX
    _TRX_AMOUNT_DECIMALS = const(6)

    return f"{strings.format_amount(amount, _TRX_AMOUNT_DECIMALS)} TRX"


async def confirm_transfer_contract(msg: TronTransferContract) -> None:
    to_address = base58.encode_check(msg.to_address)
    await layouts.confirm_address(
        TR.send__title_sending_to,
        to_address,
        chunkify=True,
    )
