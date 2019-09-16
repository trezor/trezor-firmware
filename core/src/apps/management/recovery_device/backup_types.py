_BIP39_WORD_COUNTS = (12, 18, 24)
_SLIP39_WORD_COUNTS = (20, 33)


def is_slip39_word_count(word_count: int) -> bool:
    """
    Returns True for SLIP-39 and False for BIP-39.
    Raise RuntimeError otherwise.
    """
    if word_count in _SLIP39_WORD_COUNTS:
        return True
    elif word_count in _BIP39_WORD_COUNTS:
        return False
    # Unknown word count.
    raise RuntimeError
