from micropython import const
from ustruct import unpack

from trezor.strings import format_amount

_OMNI_DECIMALS = const(8)

currencies = {
    1: ("OMNI", _OMNI_DECIMALS),
    2: ("tOMNI", _OMNI_DECIMALS),
    3: ("MAID", 0),
    31: ("USDT", _OMNI_DECIMALS),
}


def is_valid(data: bytes) -> bool:
    return len(data) >= 8 and data[:4] == b"omni"


def parse(data: bytes) -> str:
    if not is_valid(data):
        raise ValueError  # tried to parse data that fails validation
    tx_version, tx_type = unpack(">HH", data[4:8])
    if tx_version == 0 and tx_type == 0 and len(data) == 20:  # OMNI simple send
        currency, amount = unpack(">IQ", data[8:20])
        suffix, decimals = currencies.get(currency, ("UNKN", 0))
        return f"Simple send of {format_amount(amount, decimals)} {suffix}"
    else:
        # unknown OMNI transaction
        return "Unknown transaction"
