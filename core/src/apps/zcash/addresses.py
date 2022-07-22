"""
Implementation of encoding and decoding of Zcash
unified addresses according to the ZIP-316.

see: https://zips.z.cash/zip-0316
"""

from typing import Dict

from trezor.crypto import orchardlib
from trezor.crypto.bech32 import Encoding, bech32_decode, bech32_encode, convertbits
from trezor.enums import ZcashReceiverTypecode as Typecode
from trezor.utils import BufferReader, empty_bytearray
from trezor.wire import DataError

from apps.common.coininfo import CoinInfo
from apps.common.readers import read_compact_size
from apps.common.writers import write_bytes_fixed, write_compact_size


def receiver_length(typecode: int):
    """Byte length of a receiver."""
    if typecode == Typecode.P2PKH:
        return 20
    if typecode == Typecode.P2SH:
        return 20
    if typecode == Typecode.SAPLING:
        return 43
    if typecode == Typecode.ORCHARD:
        return 43
    raise ValueError


def unified_prefix(coin: CoinInfo):
    """Prefix for a unified address."""
    if coin.coin_name == "Zcash":
        return "u"
    if coin.coin_name == "Zcash Testnet":
        return "utest"
    raise ValueError


def padding(hrp: str) -> bytes:
    assert len(hrp) <= 16
    return bytes(hrp, "utf8") + bytes(16 - len(hrp))


def encode_unified(receivers: Dict[Typecode, bytes], coin: CoinInfo) -> str:
    # multiple transparent receivers forbidden
    assert not (Typecode.P2PKH in receivers and Typecode.P2SH in receivers)

    length = 16  # 16 bytes for padding
    for typecode in receivers.keys():
        length += 2  # typecode (1 byte) + length (1 byte)
        length += receiver_length(typecode)

    w = empty_bytearray(length)

    # receivers in decreasing order
    receivers_list = list(receivers.items())
    receivers_list.sort(reverse=True)

    for (typecode, raw_bytes) in receivers_list:
        write_compact_size(w, typecode)
        write_compact_size(w, receiver_length(typecode))
        write_bytes_fixed(w, raw_bytes, receiver_length(typecode))

    hrp = unified_prefix(coin)
    write_bytes_fixed(w, padding(hrp), 16)
    orchardlib.f4jumble(w)
    assert w is not None  # to satisfy typecheckers
    converted = convertbits(w, 8, 5)
    return bech32_encode(hrp, converted, Encoding.BECH32M)


def decode_unified(addr_str: str, coin: CoinInfo) -> Dict[int, bytes]:
    (hrp, data, encoding) = bech32_decode(addr_str, max_bech_len=1000)
    if (hrp, data, encoding) == (None, None, None):
        raise DataError("Bech32m decoding failed.")
    assert hrp is not None  # to satisfy typecheckers
    assert data is not None  # to satisfy typecheckers
    assert encoding is not None  # to satisfy typecheckers
    if hrp != unified_prefix(coin):
        raise DataError("Unexpected address prefix.")
    if encoding != Encoding.BECH32M:
        raise DataError("Bech32m encoding required.")

    decoded = bytearray(convertbits(data, 5, 8, False))
    orchardlib.f4jumble_inv(decoded)

    # check trailing padding bytes
    if decoded[-16:] != padding(hrp):
        raise DataError("Invalid padding bytes")

    r = BufferReader(decoded[:-16])

    last_typecode = None
    receivers = {}
    while r.remaining_count() > 0:
        typecode = read_compact_size(r)
        if typecode in receivers:
            raise DataError("Duplicated typecode")
        if typecode > 0x02000000:
            raise DataError("Invalid typecode")
        if last_typecode is not None and typecode > last_typecode:
            raise DataError("Invalid receivers order")
        last_typecode = typecode

        length = read_compact_size(r)
        # if the typecode of the receiver is known, then verify receiver length
        try:
            expected_length = receiver_length(typecode)
            if length != expected_length:
                raise DataError("Unexpected receiver length")
        except ValueError:
            pass

        if r.remaining_count() < length:
            raise DataError("Invalid receiver length")

        receivers[typecode] = r.read(length)

    return receivers
