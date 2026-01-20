from micropython import const
from typing import TYPE_CHECKING

from trezor.crypto import base32

if TYPE_CHECKING:
    from buffer_types import AnyBytes

# Stellar strkey version bytes
# See: https://github.com/stellar/stellar-protocol/blob/master/ecosystem/sep-0023.md
STRKEY_ED25519_PUBLIC_KEY = const(6)  # G...
STRKEY_CONTRACT = const(2)  # C...
STRKEY_MUXED_ACCOUNT = const(12)  # M...
STRKEY_CLAIMABLE_BALANCE = const(1)  # B...
STRKEY_LIQUIDITY_POOL = const(11)  # L...

_PAYLOAD_SIZE = {
    STRKEY_ED25519_PUBLIC_KEY: 32,
    STRKEY_CONTRACT: 32,
    STRKEY_MUXED_ACCOUNT: 40,
    STRKEY_CLAIMABLE_BALANCE: 33,
    STRKEY_LIQUIDITY_POOL: 32,
}


def public_key_from_address(address: str) -> bytes:
    """Extracts public key from an address
    Stellar address is in format:
    <1-byte version> <32-bytes ed25519 public key> <2-bytes CRC-16 checksum>
    """
    from trezor.wire import DataError

    version, data = decode_strkey(address)
    if version != STRKEY_ED25519_PUBLIC_KEY:
        raise DataError("Expected a public key address")
    return data


def address_from_public_key(pubkey: AnyBytes) -> str:
    """Returns the base32-encoded version of public key bytes (G...)"""
    return encode_strkey(STRKEY_ED25519_PUBLIC_KEY, pubkey)


def encode_strkey(version: int, data: AnyBytes) -> str:
    """Encode data to Stellar strkey format."""
    payload = bytearray()
    payload.append(version << 3)
    payload.extend(data)
    payload.extend(_crc16_checksum(bytes(payload)))
    return base32.encode(payload).rstrip("=")


def decode_strkey(strkey: str) -> tuple[int, bytes]:
    """Decode and validate a Stellar strkey into (version, data).

    Follows SEP-0023: strkeys are unpadded base32, so the `=` padding stripped
    by `encode_strkey` is restored before decoding. Besides the CRC-16 checksum,
    canonicality is enforced by re-encoding: any input with an invalid length,
    non-zero unused bits or an unsupported algorithm re-encodes differently and
    is rejected.
    """
    from trezor.wire import DataError

    try:
        b = base32.decode(strkey + "=" * (-len(strkey) % 8))
    except ValueError:
        raise DataError("Strkey not base32-encoded")
    if _crc16_checksum(b[:-2]) != b[-2:]:
        raise DataError("Invalid strkey checksum")
    version = b[0] >> 3
    data = b[1:-2]
    if encode_strkey(version, data) != strkey:
        raise DataError("Invalid strkey encoding")
    if version not in _PAYLOAD_SIZE:
        raise DataError("Unsupported strkey version")
    if len(data) != _PAYLOAD_SIZE[version]:
        raise DataError("Invalid strkey payload length")
    if version == STRKEY_CLAIMABLE_BALANCE and data[0] != 0:
        # only CLAIMABLE_BALANCE_ID_TYPE_V0 exists
        raise DataError("Invalid claimable balance type")
    return version, data


def _crc16_checksum(data: AnyBytes) -> bytes:
    """Returns the CRC-16 checksum of bytearray bytes

    Ported from Java implementation at: http://introcs.cs.princeton.edu/java/61data/CRC16CCITT.java.html

    Initial value changed to 0x0000 to match Stellar configuration.
    """
    import ustruct

    crc = 0x0000
    polynomial = 0x1021

    for byte in data:
        for i in range(8):
            bit = (byte >> (7 - i) & 1) == 1
            c15 = (crc >> 15 & 1) == 1
            crc <<= 1
            if c15 ^ bit:
                crc ^= polynomial

    return ustruct.pack("<H", crc & 0xFFFF)
