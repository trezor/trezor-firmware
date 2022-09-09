"""
Implementation of encoding and decoding of Zcash
unified addresses according to the ZIP-316.
see: https://zips.z.cash/zip-0316
"""

from typing import TYPE_CHECKING

from trezor.crypto.bech32 import Encoding, bech32_decode, bech32_encode, convertbits
from trezor.utils import BufferReader, empty_bytearray
from trezor.wire import DataError

from apps.common.coininfo import CoinInfo
from apps.common.readers import read_compact_size
from apps.common.writers import write_bytes_fixed, write_compact_size

from .f4jumble import f4jumble, f4unjumble

if TYPE_CHECKING:
    from enum import IntEnum
else:
    IntEnum = object


class Typecode(IntEnum):
    P2PKH = 0x00
    P2SH = 0x01
    SAPLING = 0x02
    ORCHARD = 0x03


def receiver_length(typecode: int) -> int | None:
    """Byte length of a receiver."""
    if typecode in (Typecode.P2PKH, Typecode.P2SH):
        return 20
    if typecode in (Typecode.SAPLING, Typecode.ORCHARD):
        return 43
    return None


def prefix(coin: CoinInfo) -> str:
    """Prefix for a unified address."""
    if coin.coin_name == "Zcash":
        return "u"
    if coin.coin_name == "Zcash Testnet":
        return "utest"
    raise ValueError


def padding(hrp: str) -> bytes:
    assert len(hrp) <= 16
    return hrp.encode() + bytes(16 - len(hrp))


def encode(receivers: dict[Typecode, bytes], coin: CoinInfo) -> str:
    # multiple transparent receivers forbidden
    assert not (Typecode.P2PKH in receivers and Typecode.P2SH in receivers)
    # at least one shielded address must be present
    assert Typecode.SAPLING in receivers or Typecode.ORCHARD in receivers

    length = 16  # 16 bytes for padding
    for receiver_bytes in receivers.values():
        length += 2  # typecode (1 byte) + length (1 byte)
        length += len(receiver_bytes)

    w = empty_bytearray(length)

    # receivers in ascending order
    receivers_list = list(receivers.items())
    receivers_list.sort()

    for (typecode, raw_bytes) in receivers_list:
        length = receiver_length(typecode) or len(raw_bytes)
        write_compact_size(w, typecode)
        write_compact_size(w, length)
        write_bytes_fixed(w, raw_bytes, length)

    hrp = prefix(coin)
    write_bytes_fixed(w, padding(hrp), 16)
    f4jumble(memoryview(w))
    converted = convertbits(w, 8, 5)
    return bech32_encode(hrp, converted, Encoding.BECH32M)


def decode(addr_str: str, coin: CoinInfo) -> dict[int, bytes]:
    try:
        hrp, data, encoding = bech32_decode(addr_str, 1000)
    except ValueError:
        raise DataError("Bech32m decoding failed.")
    assert hrp is not None  # to satisfy typecheckers
    assert data is not None  # to satisfy typecheckers
    assert encoding is not None  # to satisfy typecheckers
    if hrp != prefix(coin):
        raise DataError("Unexpected address prefix.")
    if encoding != Encoding.BECH32M:
        raise DataError("Bech32m encoding required.")

    decoded = bytearray(convertbits(data, 5, 8, False))
    f4unjumble(memoryview(decoded))

    # check trailing padding bytes
    if decoded[-16:] != padding(hrp):
        raise DataError("Invalid padding bytes")

    r = BufferReader(decoded[:-16])

    last_typecode = None
    receivers: dict[int, bytes] = dict()
    while r.remaining_count() > 0:
        typecode = read_compact_size(r)
        if typecode in receivers:
            raise DataError("Duplicated typecode")
        if typecode > 0x02000000:
            raise DataError("Invalid typecode")
        if last_typecode is not None and typecode < last_typecode:
            raise DataError("Invalid receivers order")
        last_typecode = typecode

        length = read_compact_size(r)
        # if the typecode of the receiver is known, then verify receiver length
        expected_length = receiver_length(typecode)
        if expected_length is not None and length != expected_length:
            raise DataError("Unexpected receiver length")

        if r.remaining_count() < length:
            raise DataError("Invalid receiver length")

        receivers[typecode] = r.read(length)

    if Typecode.P2PKH in receivers and Typecode.P2SH in receivers:
        raise DataError("Multiple transparent receivers")

    if len(receivers) == 1:
        the_receiver = list(receivers.keys())[0]
        if the_receiver in (Typecode.P2PKH, Typecode.P2SH):
            raise DataError("Only transparent receiver")

    return receivers
