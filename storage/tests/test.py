#!/usr/bin/env python3

from hashlib import sha256

from c.storage import Storage as StorageC
from python.src.storage import Storage as StoragePy


def hash(data):
    return sha256(data).hexdigest()[:16]


# Strings for testing ChaCha20 encryption.
test_strings = [
    b"Short string.",
    b"",
    b"Although ChaCha20 is a stream cipher, it operates on blocks of 64 bytes. This string is over 152 bytes in length so that we test multi-block encryption.",
    b"This string is exactly 64 bytes long, that is exactly one block.",
]

# Unique device ID for testing.
uid = b"\x67\xce\x6a\xe8\xf7\x9b\x73\x96\x83\x88\x21\x5e"

sc = StorageC()
sp = StoragePy()
a = []

for s in [sc, sp]:
    print(s.__class__)
    s.init(uid)
    assert s.unlock(3) is False
    assert s.unlock(1) is True
    s.set(0xBEEF, b"hello")
    s.set(0x03FE, b"world!")
    s.set(0xBEEF, b"satoshi")
    s.set(0xBEEF, b"Satoshi")
    for value in test_strings:
        s.set(0x0301, value)
        assert s.get(0x0301) == value
    d = s._dump()
    print(d[0][:512].hex())
    h = [hash(x) for x in d]
    print(h)
    a.append(h[0])
    a.append(h[1])
    print()

print("-------------")
print("Equals:", a[0] == a[2] and a[1] == a[3])
