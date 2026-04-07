def derive_addr(pubkey: bytes, prefix: str) -> str:
    """
    Derive a Cosmos bech32 address from a public key.

    Args:
        pubkey: Compressed secp256k1 public key (33 bytes).
        prefix: Bech32 prefix for the target chain.

    Returns:
        Bech32-encoded Cosmos address.
    """
    from trezor.crypto import bech32

    address_bz = derive_addr_bz(pubkey)
    converted_bits = bech32.convertbits(address_bz, 8, 5)
    return bech32.bech32_encode(prefix, converted_bits, bech32.Encoding.BECH32)


def derive_addr_bz(pubkey: bytes) -> bytes:
    """
    Derive raw Cosmos address bytes from a public key.

    Uses SHA256 followed by RIPEMD160, matching the standard Cosmos account
    address derivation for secp256k1 keys.

    Args:
        pubkey: Compressed secp256k1 public key (33 bytes).

    Returns:
        Raw 20-byte address payload.
    """
    from trezor.crypto.hashlib import ripemd160, sha256

    return ripemd160(sha256(pubkey).digest()).digest()
