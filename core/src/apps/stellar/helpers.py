from micropython import const
from typing import TYPE_CHECKING

from trezor.crypto import base32

if TYPE_CHECKING:
    from buffer_types import AnyBytes

    from trezor.messages import StellarAsset, StellarInvokeContractArgs

    from .layout import StellarToken

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


def sac_address_from_asset(network_id: AnyBytes, asset: StellarAsset) -> str:
    """Derive the address of the Stellar Asset Contract (SAC) of an asset (C...).

    See https://github.com/stellar/stellar-protocol/blob/master/core/cap-0046-02.md#contract-identifier-preimage-type
    """
    from trezor.crypto.hashlib import sha256

    from .writers import write_asset, write_bytes_fixed, write_uint32

    w = bytearray()
    write_uint32(w, 8)  # ENVELOPE_TYPE_CONTRACT_ID
    write_bytes_fixed(w, network_id, 32)
    write_uint32(w, 1)  # CONTRACT_ID_PREIMAGE_FROM_ASSET
    write_asset(w, asset)
    return encode_strkey(STRKEY_CONTRACT, sha256(w).digest())


def resolve_sep41_token(
    args: StellarInvokeContractArgs, network_id: AnyBytes
) -> StellarToken | None:
    """Resolve token metadata for the dedicated SEP-41 UI.

    A contract is recognized in two ways. The host may identify a Stellar Asset
    Contract by supplying its underlying asset; the hint is used only when its
    derived SAC address matches the invoked contract, so it cannot mislead the
    user. Otherwise the contract may be one of the tokens hard-coded in the
    firmware, which are vetted in advance and need no host cooperation at all.

    A SAC match is cryptographically proven, so it takes precedence. Anything
    left unrecognized goes to the generic contract UI.
    """
    from trezor.crypto.hashlib import sha256
    from trezor.wire import DataError

    from . import consts
    from .layout import StellarToken

    contract = args.contract_address
    asset = args.asset_hint
    if asset is not None:
        try:
            if sac_address_from_asset(network_id, asset) == contract:
                return StellarToken.from_asset(asset)
        except DataError:
            pass

    if network_id == sha256(consts.NETWORK_PASSPHRASE_PUBLIC.encode()).digest():
        known = consts.PUBLIC_TOKENS.get(contract)
        if known is not None:
            symbol, decimals = known
            return StellarToken(symbol, decimals, issuer=None)
    return None


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
    import struct

    crc = 0x0000
    polynomial = 0x1021

    for byte in data:
        for i in range(8):
            bit = (byte >> (7 - i) & 1) == 1
            c15 = (crc >> 15 & 1) == 1
            crc <<= 1
            if c15 ^ bit:
                crc ^= polynomial

    return struct.pack("<H", crc & 0xFFFF)
