from typing import TYPE_CHECKING

from trezor.enums import MessageType

if TYPE_CHECKING:
    from buffer_types import AnyBytes
    from typing import Iterator, Tuple

TYPE_URL_TEMPLATE = "type.googleapis.com/protocol."

CONTRACT_TYPES = (
    MessageType.TronTransferContract,
    MessageType.TronVoteWitnessContract,
    MessageType.TronTriggerSmartContract,
    MessageType.TronFreezeBalanceV2Contract,
    MessageType.TronUnfreezeBalanceV2Contract,
    MessageType.TronWithdrawUnfreeze,
    MessageType.TronWithdrawBalance,
)

# https://github.com/tronprotocol/protocol/blob/37bb922a9967bbbef1e84de1c9e5cda56a2d7998/core/Tron.proto#L339-L379
CONTRACT_TYPE_NAMES = {
    1: "TransferContract",
    4: "VoteWitnessContract",
    13: "WithdrawBalanceContract",
    31: "TriggerSmartContract",
    54: "FreezeBalanceV2Contract",
    55: "UnfreezeBalanceV2Contract",
    56: "WithdrawExpireUnfreezeContract",
}


def get_contract_type_name(contract_type: int) -> str:
    """Get contract type name by its number."""
    if contract_type in CONTRACT_TYPE_NAMES:
        return CONTRACT_TYPE_NAMES[contract_type]
    raise ValueError(f"Unknown contract type: {contract_type}")


# TRC-20 token address bytes (21-byte, 0x41-prefixed)
_SHASTA_USDT_ADDRESS = b"\x41\x42\xa1\xe3\x9a\xef\xa4\x92\x90\xf2\xb3\xf9\xed\x68\x8d\x7c\xec\xf8\x6c\xd6\xe0"
_USDT_ADDRESS = b"\x41\xa6\x14\xf8\x03\xb6\xfd\x78\x09\x86\xa4\x2c\x78\xec\x9c\x7f\x77\xe6\xde\xd1\x3c"
_USDD_ADDRESS = b"\x41\xe9\x1a\x74\x11\xe5\x6c\xe7\x9e\x83\x57\x05\x70\xf4\x9b\x9f\xc3\x5b\x77\x27\xc5"
_SUN_ADDRESS = b"\x41\xb4\xa4\x28\xab\x70\x92\xc2\xf1\x39\x5f\x37\x6c\xe2\x97\x03\x3b\x3b\xb4\x46\xc1"
_JST_ADDRESS = b"\x41\x18\xfd\x06\x26\xda\xf3\xaf\x02\x38\x9a\xef\x3e\xd8\x7d\xb9\xc3\x3f\x63\x8f\xfa"
_BTT_ADDRESS = b"\x41\x03\x20\x17\x41\x1f\x46\x63\xb3\x17\xfe\x77\xc2\x57\xd2\x8d\x5c\xd1\xb2\x6e\x3d"
_WIN_ADDRESS = b"\x41\x74\x47\x2e\x7d\x35\x39\x5a\x6b\x5a\xdd\x42\x7e\xec\xb7\xf4\xb6\x2a\xd2\xb0\x71"
_WBTC_ADDRESS = b"\x41\xf9\x53\x35\xa4\xd4\x2d\xb4\xb7\x0a\x96\x88\xa3\x93\x27\x9f\x2c\x90\xfa\x10\x25"
_ETH_TRON_ADDRESS = b"\x41\x53\x90\x83\x08\xf4\xaa\x22\x0f\xb1\x0d\x77\x8b\x5d\x1b\x34\x48\x9c\xd6\xed\xfc"
_USD1_ADDRESS = b"\x41\x91\xbe\xd8\xe7\x84\x24\x9c\x91\x61\x1e\x61\xc4\x58\x5c\x40\xe2\x1f\xd0\xac\xe2"
_HTX_ADDRESS = b"\x41\xca\x03\x03\xe8\xb9\xa7\x38\x12\x17\x77\x11\x6d\xce\xa4\x19\xfe\x52\x4f\x27\x1a"
_TUSD_ADDRESS = b"\x41\xce\xbd\xe7\x10\x77\xb8\x30\xb9\x58\xc8\xda\x17\xbc\xdd\xee\xb8\x5d\x0b\xcf\x25"
_WBT_ADDRESS = b"\x41\x40\x3e\x0f\xfc\xa2\x31\xf6\x0f\x8d\x3e\xba\xd4\x26\xf7\x7a\xa6\xb5\x07\x30\x9d"
_WTRX_ADDRESS = b"\x41\x89\x1c\xdb\x91\xd1\x49\xf2\x3b\x1a\x45\xd9\xc5\xca\x78\xa8\x8d\x0c\xb4\x4c\x18"
_SUNOLD_ADDRESS = b"\x41\x6b\x51\x51\x32\x03\x59\xec\x18\xb0\x86\x07\xc7\x0a\x3b\x74\x39\xaf\x62\x6a\xa3"
_AINFT_ADDRESS = b"\x41\x3d\xfe\x63\x7b\x2b\x9a\xe4\x19\x0a\x45\x8b\x5f\x3e\xfc\x19\x69\xaf\xe2\x78\x19"
_STRX_ADDRESS = b"\x41\xc6\x4e\x69\xac\xde\x1c\x7b\x16\xc2\xa3\xef\xcd\xbb\xda\xa9\x6c\x36\x44\xc2\xb3"
_KLEVER_ADDRESS = b"\x41\xd8\xb8\x08\x98\x56\xce\xd3\x03\x86\x01\xcb\xeb\x1e\x3f\x76\x5c\xab\xc1\x2a\x41"


def token_iterator() -> Iterator[Tuple[AnyBytes, int, str]]:
    yield (_SHASTA_USDT_ADDRESS, 6, "tUSDT")
    yield (_USDT_ADDRESS, 6, "USDT")
    yield (_USDD_ADDRESS, 18, "USDD")
    yield (_SUN_ADDRESS, 18, "SUN")
    yield (_JST_ADDRESS, 18, "JST")
    yield (_BTT_ADDRESS, 18, "BTT")
    yield (_WIN_ADDRESS, 6, "WIN")
    yield (_WBTC_ADDRESS, 8, "WBTC")
    yield (_ETH_TRON_ADDRESS, 18, "ETH(Tron)")
    yield (_USD1_ADDRESS, 18, "USD1")
    yield (_HTX_ADDRESS, 18, "HTX")
    yield (_TUSD_ADDRESS, 18, "TUSD")
    yield (_WBT_ADDRESS, 8, "WBT")
    yield (_WTRX_ADDRESS, 6, "WTRX")
    yield (_SUNOLD_ADDRESS, 18, "SUNOLD")
    yield (_AINFT_ADDRESS, 6, "AINFT")
    yield (_STRX_ADDRESS, 18, "sTRX")
    yield (_KLEVER_ADDRESS, 6, "Klever")
