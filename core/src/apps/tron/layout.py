from micropython import const
from typing import TYPE_CHECKING

import trezor.ui.layouts as layouts
from trezor import TR, strings

from .helpers import get_encoded_address

if TYPE_CHECKING:
    from trezor.messages import (
        EthereumTokenInfo,
        TronTransferContract,
        TronTriggerSmartContract,
    )


def format_trx_amount(amount: int) -> str:
    # 1 SUN = 0.000001 TRX
    _TRX_AMOUNT_DECIMALS = const(6)

    return f"{strings.format_amount(amount, _TRX_AMOUNT_DECIMALS)} TRX"


def format_token_amount(amount: int, token: EthereumTokenInfo) -> str:
    return f"{strings.format_amount(amount, token.decimals)} {token.symbol}"


def format_energy_amount(amount: int) -> str:
    return f"{strings.format_amount(amount, 0)} SUN"


async def confirm_transfer_contract(contract: TronTransferContract) -> None:
    to_address = get_encoded_address(contract.to_address)

    await layouts.confirm_address(
        TR.send__title_sending_to,
        to_address,
        chunkify=True,
    )


# TODO: Refactor ETH references to crypto-neutral references.
async def confirm_unknown_smart_contract(
    contract: TronTriggerSmartContract, fee_limit: int
) -> None:

    from trezor.enums import ButtonRequestType
    from trezor.ui.layouts import (
        confirm_address,
        confirm_blob,
        confirm_ethereum_unknown_contract_warning,
        confirm_tron_send,
    )

    await confirm_ethereum_unknown_contract_warning(TR.words__send)

    contract_address = get_encoded_address(contract.contract_address)
    await confirm_address(
        title=TR.ethereum__token_contract,
        address=contract_address,
        chunkify=True,
    )

    await confirm_blob(
        "confirm_smart_contract_data",
        TR.ethereum__title_input_data,
        contract.data,
        chunkify=False,
        verb=TR.buttons__confirm,
        verb_cancel=TR.send__cancel_sign,
        br_code=ButtonRequestType.SignTx,
        ask_pagination=True,
    )

    await confirm_tron_send(None, format_energy_amount(fee_limit))


async def confirm_known_trc20_smart_contract(
    recipient_addr: bytes, amount: int, fee_limit: int, token: EthereumTokenInfo
) -> None:
    from trezor.ui.layouts import confirm_tron_transfer

    await confirm_tron_transfer(
        recipient_addr=get_encoded_address(recipient_addr),
        total_amount=format_token_amount(amount, token),
        maximum_fee=format_energy_amount(fee_limit),
        chunkify=True,
    )
