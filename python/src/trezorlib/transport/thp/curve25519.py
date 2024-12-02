from typing import Tuple

p = 2**255 - 19
J = 486662

c3 = 19681161376707505956807079304988542015446066515923890162744021073123829784752  # sqrt(-1)
c4 = 7237005577332262213973186563042994240829374041602535252466099000494570602493  # (p - 5) // 8
a24 = 121666  # (J + 2) // 4


def decode_scalar(scalar: bytes) -> int:
    # decodeScalar25519 from
    # https://datatracker.ietf.org/doc/html/rfc7748#section-5

    if len(scalar) != 32:
        raise ValueError("Invalid length of scalar")

    array = bytearray(scalar)
    array[0] &= 248
    array[31] &= 127
    array[31] |= 64

    return int.from_bytes(array, "little")


def decode_coordinate(coordinate: bytes) -> int:
    # decodeUCoordinate from
    # https://datatracker.ietf.org/doc/html/rfc7748#section-5
    if len(coordinate) != 32:
        raise ValueError("Invalid length of coordinate")

    array = bytearray(coordinate)
    array[-1] &= 0x7F
    return int.from_bytes(array, "little") % p


def encode_coordinate(coordinate: int) -> bytes:
    # encodeUCoordinate from
    # https://datatracker.ietf.org/doc/html/rfc7748#section-5
    return coordinate.to_bytes(32, "little")


def get_private_key(secret: bytes) -> bytes:
    return decode_scalar(secret).to_bytes(32, "little")


def get_public_key(private_key: bytes) -> bytes:
    base_point = int.to_bytes(9, 32, "little")
    return multiply(private_key, base_point)


def multiply(private_scalar: bytes, public_point: bytes):
    # X25519 from
    # https://datatracker.ietf.org/doc/html/rfc7748#section-5

    def ladder_operation(
        x1: int, x2: int, z2: int, x3: int, z3: int
    ) -> Tuple[int, int, int, int]:
        # https://hyperelliptic.org/EFD/g1p/auto-montgom-xz.html#ladder-ladd-1987-m-3
        # (x4, z4) = 2 * (x2, z2)
        # (x5, z5) = (x2, z2) + (x3, z3)
        # where (x1, 1) = (x3, z3) - (x2, z2)

        a = (x2 + z2) % p
        aa = (a * a) % p
        b = (x2 - z2) % p
        bb = (b * b) % p
        e = (aa - bb) % p
        c = (x3 + z3) % p
        d = (x3 - z3) % p
        da = (d * a) % p
        cb = (c * b) % p
        t0 = (da + cb) % p
        x5 = (t0 * t0) % p
        t1 = (da - cb) % p
        t2 = (t1 * t1) % p
        z5 = (x1 * t2) % p
        x4 = (aa * bb) % p
        t3 = (a24 * e) % p
        t4 = (bb + t3) % p
        z4 = (e * t4) % p

        return x4, z4, x5, z5

    def conditional_swap(first: int, second: int, condition: int):
        # Returns (second, first) if condition is true and (first, second) otherwise
        # Must be implemented in a way that it is constant time
        true_mask = -condition
        false_mask = ~true_mask
        return (first & false_mask) | (second & true_mask), (second & false_mask) | (
            first & true_mask
        )

    k = decode_scalar(private_scalar)
    u = decode_coordinate(public_point)

    x_1 = u
    x_2 = 1
    z_2 = 0
    x_3 = u
    z_3 = 1
    swap = 0

    for i in reversed(range(256)):
        bit = (k >> i) & 1
        swap = bit ^ swap
        (x_2, x_3) = conditional_swap(x_2, x_3, swap)
        (z_2, z_3) = conditional_swap(z_2, z_3, swap)
        swap = bit
        x_2, z_2, x_3, z_3 = ladder_operation(x_1, x_2, z_2, x_3, z_3)

    (x_2, x_3) = conditional_swap(x_2, x_3, swap)
    (z_2, z_3) = conditional_swap(z_2, z_3, swap)

    x = pow(z_2, p - 2, p) * x_2 % p
    return encode_coordinate(x)
