# Base32 implementation taken from the micropython-lib's base64 module
# https://github.com/micropython/micropython-lib/blob/master/base64/base64.py
#

from ubinascii import unhexlify
from ustruct import unpack


_b32alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567'

_b32tab = [ord(c) for c in _b32alphabet]
_b32rev = dict([(ord(v), k) for k, v in enumerate(_b32alphabet)])


def encode(s: bytes) -> str:
    quanta, leftover = divmod(len(s), 5)
    # Pad the last quantum with zero bits if necessary
    if leftover:
        s = s + bytes(5 - leftover)  # Don't use += !
        quanta += 1
    encoded = bytearray()
    for i in range(quanta):
        # c1 and c2 are 16 bits wide, c3 is 8 bits wide.  The intent of this
        # code is to process the 40 bits in units of 5 bits.  So we take the 1
        # leftover bit of c1 and tack it onto c2.  Then we take the 2 leftover
        # bits of c2 and tack them onto c3.  The shifts and masks are intended
        # to give us values of exactly 5 bits in width.
        c1, c2, c3 = unpack('!HHB', s[i * 5:(i + 1) * 5])
        c2 += (c1 & 1) << 16  # 17 bits wide
        c3 += (c2 & 3) << 8   # 10 bits wide
        encoded += bytes([_b32tab[c1 >> 11],          # bits 1 - 5
                          _b32tab[(c1 >> 6) & 0x1f],  # bits 6 - 10
                          _b32tab[(c1 >> 1) & 0x1f],  # bits 11 - 15
                          _b32tab[c2 >> 12],          # bits 16 - 20 (1 - 5)
                          _b32tab[(c2 >> 7) & 0x1f],  # bits 21 - 25 (6 - 10)
                          _b32tab[(c2 >> 2) & 0x1f],  # bits 26 - 30 (11 - 15)
                          _b32tab[c3 >> 5],           # bits 31 - 35 (1 - 5)
                          _b32tab[c3 & 0x1f],         # bits 36 - 40 (1 - 5)
                          ])
    # Adjust for any leftover partial quanta
    if leftover == 1:
        encoded = encoded[:-6] + b'======'
    elif leftover == 2:
        encoded = encoded[:-4] + b'===='
    elif leftover == 3:
        encoded = encoded[:-3] + b'==='
    elif leftover == 4:
        encoded = encoded[:-1] + b'='

    return bytes(encoded).decode()


def decode(s: str) -> bytes:
    s = s.encode()
    quanta, leftover = divmod(len(s), 8)
    if leftover:
        raise ValueError('Incorrect padding')
    # Strip off pad characters from the right.  We need to count the pad
    # characters because this will tell us how many null bytes to remove from
    # the end of the decoded string.
    padchars = s.find(b'=')
    if padchars > 0:
        padchars = len(s) - padchars
        s = s[:-padchars]
    else:
        padchars = 0

    # Now decode the full quanta
    parts = []
    acc = 0
    shift = 35
    for c in s:
        val = _b32rev.get(c)
        if val is None:
            raise ValueError('Non-base32 digit found')
        acc += _b32rev[c] << shift
        shift -= 5
        if shift < 0:
            parts.append(unhexlify(('%010x' % acc).encode()))
            acc = 0
            shift = 35
    # Process the last, partial quanta
    last = unhexlify(bytes('%010x' % acc, "ascii"))
    if padchars == 0:
        last = b''                      # No characters
    elif padchars == 1:
        last = last[:-1]
    elif padchars == 3:
        last = last[:-2]
    elif padchars == 4:
        last = last[:-3]
    elif padchars == 6:
        last = last[:-4]
    else:
        raise ValueError('Incorrect padding')
    parts.append(last)
    return b''.join(parts)
