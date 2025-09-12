from micropython import const
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from buffer_types import AnyBytes


_OMNI_DECIMALS = const(8)

currencies = {
    1: ("OMNI", _OMNI_DECIMALS),
    2: ("tOMNI", _OMNI_DECIMALS),
    3: ("MAID", 0),
    31: ("USDT", _OMNI_DECIMALS),
}


def is_valid(data: AnyBytes) -> bool:
    return len(data) >= 8 and data[:4] == b"omni"


def parse(data: AnyBytes) -> str:
    from ustruct import unpack

    from trezor import TR
    from trezor.strings import format_amount, format_amount_unit

    if not is_valid(data):
        raise ValueError  # tried to parse data that fails validation
    tx_version, tx_type = unpack(">HH", data[4:8])
    if tx_version == 0 and tx_type == 0 and len(data) == 20:  # OMNI simple send
        currency, amount = unpack(">IQ", data[8:20])
        suffix, decimals = currencies.get(currency, ("UNKN", 0))
        return f"{TR.bitcoin__simple_send_of} {format_amount_unit(format_amount(amount, decimals), suffix)}"
    else:
        # unknown OMNI transaction
        return TR.bitcoin__unknown_transaction
