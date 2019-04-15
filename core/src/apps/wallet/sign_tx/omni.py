from ustruct import unpack

from trezor.utils import format_amount

currencies = {1: "OMNI", 2: "tOMNI", 3: "MAID", 31: "USDT"}


def is_valid(data: bytes) -> bool:
    return len(data) >= 8 and data[:4] == b"omni"


def parse(data: bytes) -> bool:
    if not is_valid(data):
        return None
    tx_version, tx_type = unpack(">HH", data[4:8])
    if tx_version == 0 and tx_type == 0 and len(data) == 20:  # OMNI simple send
        currency, amount = unpack(">IQ", data[8:20])
        return "Simple send of %s %s" % (
            format_amount(amount, 8),
            currencies.get(currency, "UNKN"),
        )
    else:
        # unknown OMNI transaction
        return "Unknown transaction"
