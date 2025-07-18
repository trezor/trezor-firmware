from trezor.crypto import base58


def address_from_public_key(pubkey: bytes) -> str:
    from trezor.crypto.hashlib import sha3_256

    address_bytes = b"\x41" + sha3_256(pubkey[1:], keccak=True).digest()[12:]
    return base58.encode_check(address_bytes)


def decode_address(address: str) -> bytes:
    """Decodes a Tron address into its raw bytes."""
    decoded = base58.decode_check(address)
    if decoded[0] != 0x41:
        raise ValueError("Invalid Tron address prefix")
    return decoded
