from typing import *

# extmod/modtrezorutils/modtrezorutils.c
def consteq(sec: bytes, pub: bytes) -> bool:
    '''
    Compares the private information in `sec` with public, user-provided
    information in `pub`.  Runs in constant time, corresponding to a length
    of `pub`.  Can access memory behind valid length of `sec`, caller is
    expected to avoid any invalid memory access.
    '''

# extmod/modtrezorutils/modtrezorutils.c
def memcpy(dst: bytearray, dst_ofs: int,
           src: bytearray, src_ofs: int,
           n: int) -> int:
    '''
    Copies at most `n` bytes from `src` at offset `src_ofs` to
    `dst` at offset `dst_ofs`.  Returns the number of actually
    copied bytes.
    '''

# extmod/modtrezorutils/modtrezorutils.c
def halt(msg: str = None) -> None:
    '''
    Halts execution.
    '''

# extmod/modtrezorutils/modtrezorutils.c
def set_mode_unprivileged() -> None:
    '''
    Set unprivileged mode.
    '''

# extmod/modtrezorutils/modtrezorutils.c
def symbol(name: str) -> str/int/None:
    '''
    Retrieve internal symbol.
    '''

# extmod/modtrezorutils/modtrezorutils.c
def model() -> str:
    '''
    Return which hardware model we are running on.
    '''
