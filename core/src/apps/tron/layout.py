from typing import TYPE_CHECKING

import trezor.ui.layouts as layouts
from trezor import strings, TR
from trezor.crypto import base58

from . import consts


if TYPE_CHECKING:
    from trezor.messages import TronTransferContract


def format_trx_amount(amount: int) -> str:
    return f"{strings.format_amount(amount, consts.TRX_AMOUNT_DECIMALS)} TRX"


async def confirm_transfer_contract(msg: TronTransferContract) -> None:
    to_address = base58.encode(msg.to_address)
    if to_address[0] == "T":
        raise ValueError("Tron: TransferContract: Invalid 'to_address'")
    await layouts.confirm_address(
        TR.send__title_sending_to,
        to_address,
        chunkify=True,
    )
