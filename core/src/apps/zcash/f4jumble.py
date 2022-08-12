"""
Memory-optimized implementation of F4jumble permutation specified in ZIP-316.
specification: https://zips.z.cash/zip-0316#jumbling
reference implementation: https://github.com/zcash/librustzcash/blob/main/components/f4jumble/src/lib.rs
"""

from micropython import const

from trezor.crypto.hashlib import blake2b

HASH_LENGTH = const(64)


def xor(target: memoryview, mask: bytes) -> None:
    for i in range(len(target)):
        target[i] ^= mask[i]


def G_round(i: int, left: memoryview, right: memoryview) -> None:
    for j in range((len(right) + HASH_LENGTH - 1) // HASH_LENGTH):
        mask = blake2b(
            personal=b"UA_F4Jumble_G" + bytes([i]) + j.to_bytes(2, "little"),
            data=bytes(left),
        ).digest()
        xor(right[j * HASH_LENGTH : (j + 1) * HASH_LENGTH], mask)


def H_round(i: int, left: memoryview, right: memoryview) -> None:
    mask = blake2b(
        personal=b"UA_F4Jumble_H" + bytes([i, 0, 0]),
        outlen=len(left),
        data=bytes(right),
    ).digest()
    xor(left, mask)


def f4jumble(message: memoryview) -> None:
    assert 48 <= len(message) <= 4194368
    left_length = min(HASH_LENGTH, len(message) // 2)

    left = message[:left_length]
    right = message[left_length:]
    G_round(0, left, right)
    H_round(0, left, right)
    G_round(1, left, right)
    H_round(1, left, right)


def f4unjumble(message: memoryview) -> None:
    assert 48 <= len(message) <= 4194368
    left_length = min(HASH_LENGTH, len(message) // 2)

    left = message[:left_length]
    right = message[left_length:]
    H_round(1, left, right)
    G_round(1, left, right)
    H_round(0, left, right)
    G_round(0, left, right)
