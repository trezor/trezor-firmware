from micropython import const
from typing import TYPE_CHECKING

from trezor.enums import MessageType

if TYPE_CHECKING:
    from trezor.messages import TronTransferContract

    TronMessageType = TronTransferContract

# Maximum length of the data field in TronSignTx.
MAX_DATA_LENGTH = const(256)

# Maximum Fee limit in SUN.
MAX_FEE_LIMIT = const(15_000_000_000)

# 1 SUN = 0.000001 TRX
TRX_AMOUNT_DECIMALS = const(6)

TYPE_URL_TEMPLATE = "type.googleapis.com/protocol."

CONTRACT_TYPES = (
    MessageType.TronTransferContract,
    MessageType.TronTriggerSmartContract,
)

# https://github.com/tronprotocol/protocol/blob/37bb922a9967bbbef1e84de1c9e5cda56a2d7998/core/Tron.proto#L339-L379
CONTRACT_TYPE_NAMES = {
    1: "TransferContract",
    31: "TriggerSmartContract",
}


def get_contract_type_name(contract_type: int) -> str:
    """Get contract type name by its number."""
    if contract_type in CONTRACT_TYPE_NAMES:
        return CONTRACT_TYPE_NAMES[contract_type]
    raise ValueError(f"Unknown contract type: {contract_type}")
