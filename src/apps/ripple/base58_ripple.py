from trezor.crypto import base58

# Ripple uses different 58 character alphabet than traditional base58
_ripple_alphabet = "rpshnaf39wBUDNEGHJKLM4PQRST7VWXYZ2bcdeCg65jkm8oFqi1tuvAxyz"


def encode(data: bytes) -> str:
    """
    Convert bytes to base58 encoded string.
    """
    return base58.encode(data, alphabet=_ripple_alphabet)


def decode(string: str) -> bytes:
    """
    Convert base58 encoded string to bytes.
    """
    return base58.decode(string, alphabet=_ripple_alphabet)


def encode_check(data: bytes, digestfunc=base58.sha256d_32) -> str:
    """
    Convert bytes to base58 encoded string, append checksum.
    """
    return encode(data + digestfunc(data))


def decode_check(string: str, digestfunc=base58.sha256d_32) -> bytes:
    """
    Convert base58 encoded string to bytes and verify checksum.
    """
    data = decode(string)
    return base58.verify_checksum(data, digestfunc)
