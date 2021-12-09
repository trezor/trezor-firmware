from trezor.crypto.hashlib import ripemd160, sha256

from . import base58_ripple

from apps.common import HARDENED


def bytes_to_hex(bytes):
    """
    Convert a bytes object to a hex string
    """
    result = ""
    for byte in bytes:
        result += "%02x" % byte
    return result


def account_id_from_public_key(pubkey: bytes) -> str:
    """Extracts account id from a public key"""
    h = sha256(pubkey).digest()
    h = ripemd160(h).digest()
    return h


def address_from_public_key(pubkey: bytes) -> str:
    """Extracts public key from an address

    Ripple address is in format:
    <1-byte ripple flag> <20-bytes account id> <4-bytes dSHA-256 checksum>

    - 1-byte flag is 0x00 which is 'r' (Ripple uses its own base58 alphabet)
    - 20-bytes account id is a ripemd160(sha256(pubkey))
    - checksum is first 4 bytes of double sha256(data)

    see https://xrpl.org/accounts.html#address-encoding
    """
    """Returns the Ripple address created using base58"""
    h = sha256(pubkey).digest()
    h = ripemd160(h).digest()

    address = bytearray()
    address.append(0x00)  # 'r'
    address.extend(h)
    return base58_ripple.encode_check(bytes(address))


def decode_address(address: str):
    """Returns so called Account ID"""
    adr = base58_ripple.decode_check(address)
    return adr[1:]


def validate_full_path(path: list) -> bool:
    """
    Validates derivation path to equal 44'/144'/a'/0/0,
    where `a` is an account index from 0 to 1 000 000.
    Similar to Ethereum this should be 44'/144'/a', but for
    compatibility with other HW vendors we use 44'/144'/a'/0/0.
    """
    if len(path) != 5:
        return False
    if path[0] != 44 | HARDENED:
        return False
    if path[1] != 144 | HARDENED:
        return False
    if path[2] < HARDENED or path[2] > 1000000 | HARDENED:
        return False
    if path[3] != 0:
        return False
    if path[4] != 0:
        return False
    return True


def time_from_ripple_timestamp(timestamp: int):
    """
    Converts
    Based on http://git.musl-libc.org/cgit/musl/tree/src/time/__secs_to_tm.c?h=v0.9.15
    :param timestamp: seconds since the Ripple epoch (https://xrpl.org/basic-data-types.html#specifying-time)
    :return: (year, month, day, hour, minute, second)
    """
    # Adjust to Mar 1 2000 for easier leap year calculation
    secs = timestamp - 86400 * (31 + 29)

    days = secs // 86400

    # Count 400 year cycles
    days_per_400_y = 365 * 400 + 97
    qc_cycles = days // days_per_400_y
    remdays = days % days_per_400_y
    if remdays < 0:
        remdays += days_per_400_y
        qc_cycles -= 1

    # Count remaining 100 year cycles
    days_per_100_y = 365 * 100 + 24
    c_cycles = remdays // days_per_100_y
    if c_cycles == 4:
        c_cycles -= 1
    remdays -= c_cycles * days_per_100_y

    # Count remaining 4 year cycles
    days_per_4_y = 365 * 4 + 1
    q_cycles = remdays // days_per_4_y
    if q_cycles == 25:
        q_cycles -= 1
    remdays -= q_cycles * days_per_4_y

    # Count remaining years
    remyears = remdays // 365
    if remyears == 4:
        remyears -= 1
    remdays -= remyears * 365

    # Check and account for if current year is a leap year
    leap = bool(not remyears and (q_cycles or not c_cycles))
    yday = remdays + 31 + 28 + leap
    if yday >= 365 + leap:
        yday -= 365 + leap

    # Sum up number of years since 2000
    years = remyears + 4 * q_cycles + 100 * c_cycles + 400 * qc_cycles

    # Count which month we are in
    days_in_month = [31, 30, 31, 30, 31, 31, 30, 31, 30, 31, 31, 29]
    months = 0
    while days_in_month[months] <= remdays:
        remdays -= days_in_month[months]
        months += 1

    if months > 9:
        months -= 12
        years += 1

    # How many seconds into the current day we are
    remsecs = timestamp % 86400
    return (
        years + 2000,
        months + 3,
        remdays + 1,
        remsecs // 3600,
        remsecs // 60 % 60,
        remsecs % 60,
    )


def convert_to_snake_case(word):
    return "".join(x[0].upper() + x[1:] or "_" for x in word.split("_"))
