from typing import *


# extmod/modtrezorutils/modtrezorutils.c
def consteq(sec: bytes, pub: bytes) -> bool:
    """
    Compares the private information in `sec` with public, user-provided
    information in `pub`.  Runs in constant time, corresponding to a length
    of `pub`.  Can access memory behind valid length of `sec`, caller is
    expected to avoid any invalid memory access.
    """


# extmod/modtrezorutils/modtrezorutils.c
def memcpy(
    dst: bytearray, dst_ofs: int, src: bytes, src_ofs: int, n: int
) -> int:
    """
    Copies at most `n` bytes from `src` at offset `src_ofs` to
    `dst` at offset `dst_ofs`.  Returns the number of actually
    copied bytes.
    """


# extmod/modtrezorutils/modtrezorutils.c
def halt(msg: str = None) -> None:
    """
    Halts execution.
    """
GITREV: str
VERSION_MAJOR: int
VERSION_MINOR: int
VERSION_PATCH: int
MODEL: str
EMULATOR: bool
BITCOIN_ONLY: bool
