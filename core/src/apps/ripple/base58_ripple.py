from typing import Callable

from trezor.crypto import base58

# Ripple uses different 58 character alphabet than traditional base58
_ripple_alphabet = "rpshnaf39wBUDNEGHJKLM4PQRST7VWXYZ2bcdeCg65jkm8oFqi1tuvAxyz"


def _encode(data: bytes) -> str:
    """
    Convert bytes to base58 encoded string.
    """
    return base58.encode(data, _ripple_alphabet)


def _decode(string: str) -> bytes:
    """
    Convert base58 encoded string to bytes.
    """
    return base58.decode(string, _ripple_alphabet)


def encode_check(
    data: bytes, digestfunc: Callable[[bytes], bytes] = base58.sha256d_32
) -> str:
    """
    Convert bytes to base58 encoded string, append checksum.
    """
    return _encode(data + digestfunc(data))


def decode_check(
    string: str, digestfunc: Callable[[bytes], bytes] = base58.sha256d_32
) -> bytes:
    """
    Convert base58 encoded string to bytes and verify checksum.
    """
    data = _decode(string)
    return base58.verify_checksum(data, digestfunc)
