import utime
from micropython import const

_SECONDS_1970_TO_2000 = const(946684800)


def format_amount(amount: int, decimals: int) -> str:
    if amount < 0:
        amount = -amount
        sign = "-"
    else:
        sign = ""
    d = pow(10, decimals)
    s = f"{sign}{amount // d}.{amount % d:0{decimals}}".rstrip("0").rstrip(".")
    return s


def format_ordinal(number: int) -> str:
    return str(number) + {1: "st", 2: "nd", 3: "rd"}.get(
        4 if 10 <= number % 100 < 20 else number % 10, "th"
    )


def format_plural(string: str, count: int, plural: str) -> str:
    """
    Adds plural form to a string based on `count`.
    !! Does not work with irregular words !!

    Example:
    >>> format_plural("We need {count} more {plural}", 3, "share")
    'We need 3 more shares'
    >>> format_plural("We need {count} more {plural}", 1, "share")
    'We need 1 more share'
    >>> format_plural("{count} {plural}", 4, "candy")
    '4 candies'
    """
    if not all(s in string for s in ("{count}", "{plural}")):
        # string needs to have {count} and {plural} inside
        raise ValueError

    if count == 0 or count > 1:
        # candy -> candies, but key -> keys
        if plural[-1] == "y" and plural[-2] not in "aeiouy":
            plural = plural[:-1] + "ies"
        elif plural[-1] in "hsxz":
            plural = plural + "es"
        else:
            plural = plural + "s"

    return string.format(count=count, plural=plural)


def format_duration_ms(milliseconds: int) -> str:
    """
    Returns human-friendly representation of a duration. Truncates all decimals.
    """
    units = (
        ("hour", 60 * 60 * 1000),
        ("minute", 60 * 1000),
        ("second", 1000),
    )
    for unit, divisor in units:
        if milliseconds >= divisor:
            break
    else:
        unit = "millisecond"
        divisor = 1

    return format_plural("{count} {plural}", milliseconds // divisor, unit)


def format_timestamp(timestamp: int) -> str:
    """
    Returns human-friendly representation of a unix timestamp (in seconds format).
    Minutes and seconds are always displayed as 2 digits.
    Example:
    >>> format_timestamp_to_human(0)
    '1970-01-01 00:00:00'
    >>> format_timestamp_to_human(1616051824)
    '2021-03-18 07:17:04'
    """
    # By doing the conversion to 2000-based epoch in Python, we take advantage of the
    # bignum implementation, and get another 30 years out of the 32-bit mp_int_t
    # that is used internally.
    d = utime.gmtime2000(timestamp - _SECONDS_1970_TO_2000)
    return f"{d[0]}-{d[1]:02d}-{d[2]:02d} {d[3]:02d}:{d[4]:02d}:{d[5]:02d}"
