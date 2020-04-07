from ustruct import unpack

from trezor.strings import format_amount

if False:
    from typing import Optional

currencies = {
    1: ("OMNI", True),
    2: ("tOMNI", True),
    3: ("MAID", False),
    31: ("USDT", True),
}


def is_valid(data: bytes) -> bool:
    return len(data) >= 8 and data[:4] == b"omni"


def parse(data: bytes) -> Optional[str]:
    if not is_valid(data):
        return None
    tx_version, tx_type = unpack(">HH", data[4:8])
    if tx_version == 0 and tx_type == 0 and len(data) == 20:  # OMNI simple send
        currency, amount = unpack(">IQ", data[8:20])
        suffix, divisible = currencies.get(currency, ("UNKN", False))
        return "Simple send of %s %s" % (
            format_amount(amount, 8 if divisible else 0),
            suffix,
        )
    else:
        # unknown OMNI transaction
        return "Unknown transaction"
