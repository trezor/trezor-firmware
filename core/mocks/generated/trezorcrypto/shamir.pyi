from typing import *
from buffer_types import *


# upymod/modtrezorcrypto/modtrezorcrypto-shamir.h
def interpolate(shares: Sequence[tuple[int, AnyBytes]], x: int) -> bytes:
    """
    Returns f(x) given the Shamir shares (x_1, f(x_1)), ... , (x_k, f(x_k)).
    :param shares: The Shamir shares.
    :type shares: A list of pairs (x_i, y_i), where x_i is an integer and
        y_i is an array of bytes representing the evaluations of the
        polynomials in x_i.
    :param int x: The x coordinate of the result.
    :return: Evaluations of the polynomials in x.
    :rtype: Array of bytes.
    """
