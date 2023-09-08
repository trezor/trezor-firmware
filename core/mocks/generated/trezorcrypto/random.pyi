from typing import *


# extmod/modtrezorcrypto/modtrezorcrypto-random.h
def uniform(n: int) -> int:
    """
    Compute uniform random number from interval 0 ... n - 1.
    """
import builtins


# extmod/modtrezorcrypto/modtrezorcrypto-random.h
def bytes(len: int, strong: bool = False) -> builtins.bytes:
    """
    Generate random bytes sequence of length len. If `strong` is set then
    maximum sources of entropy are used.
    """


# extmod/modtrezorcrypto/modtrezorcrypto-random.h
def shuffle(data: list) -> None:
    """
    Shuffles items of given list (in-place).
    """


# extmod/modtrezorcrypto/modtrezorcrypto-random.h
def reseed(value: int) -> None:
    """
    Re-seed the RNG with given value.
    """
