from typing import *


# extmod/modtrezorcrypto/modtrezorcrypto-slip39.h
def compute_mask(prefix: int) -> int:
    """
    Calculates which buttons still can be pressed after some already were.
    Returns a 9-bit bitmask, where each bit specifies which buttons
    can be further pressed (there are still words in this combination).
    LSB denotes first button.
    Example: 110000110 - second, third, eighth and ninth button still can be
    pressed.
    """


# extmod/modtrezorcrypto/modtrezorcrypto-slip39.h
def button_sequence_to_word(prefix: int) -> str:
    """
    Finds the first word that fits the given button prefix.
    """


# extmod/modtrezorcrypto/modtrezorcrypto-slip39.h
def word_index(word: str) -> int:
    """
    Finds index of given word.
    Raises ValueError if not found.
    """


# extmod/modtrezorcrypto/modtrezorcrypto-slip39.h
def get_word(index: int) -> str:
    """
    Returns word on position 'index'.
    """
