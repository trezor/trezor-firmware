from typing import TYPE_CHECKING

from .helpers import decode_address

if TYPE_CHECKING:
    from trezor.messages import TronRawTransferContract, TronTransferContract


def convert_transfer_contract(
    contract: TronTransferContract,
) -> TronRawTransferContract:
    from trezor.messages import TronRawTransferContract

    return TronRawTransferContract(
        owner_address=decode_address(contract.owner_address),
        to_address=decode_address(contract.to_address),
        amount=contract.amount,
    )
