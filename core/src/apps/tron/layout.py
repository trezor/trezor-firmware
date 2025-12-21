from typing import TYPE_CHECKING

import trezor.ui.layouts as layouts
from trezor import TR, strings
from trezor.crypto import base58

from . import consts

if TYPE_CHECKING:
    from trezor.messages import TronTransferContract, TronTriggerSmartContract


def format_trx_amount(amount: int) -> str:
    return f"{strings.format_amount(amount, consts.TRX_AMOUNT_DECIMALS)} TRX"


def format_energy_amount(amount: int) -> str:
    return f"{strings.format_amount(amount, 0)} SUN"


async def confirm_transfer_contract(contract: TronTransferContract) -> None:
    to_address = base58.encode_check(contract.to_address)
    await layouts.confirm_address(
        TR.send__title_sending_to,
        to_address,
        chunkify=True,
    )


async def trigger_unkown_smart_contract(contract: TronTriggerSmartContract) -> None:

    from trezor.enums import ButtonRequestType
    from trezor.ui.layouts import confirm_address, confirm_blob, confirm_ethereum_unknown_contract_warning

    await confirm_ethereum_unknown_contract_warning(TR.words__send)

    # show_danger(
    #     "unknown_contract_warning",
    #     f"{TR.ethereum__unknown_contract_address} {TR.words__know_what_your_doing}",
    #     title=TR.words__important,
    #     # menu_title=TR.words__send,
    #     verb_cancel=TR.send__cancel_sign,
    # )

    contract_address = base58.encode_check(contract.contract_address)
    await confirm_address(
        TR.ethereum__token_contract,
        contract_address,
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
