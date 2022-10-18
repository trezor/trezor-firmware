# Author: Dusan Klinec, ph4r05, 2018
#
# Resources:
# https://cr.yp.to
# https://github.com/monero-project/mininero
# https://godoc.org/github.com/agl/ed25519/edwards25519
# https://tools.ietf.org/html/draft-josefsson-eddsa-ed25519-00#section-4
# https://github.com/monero-project/research-lab

from trezor.crypto import monero as tcry
from trezor.crypto.hashlib import sha3_256

NULL_KEY_ENC = b"\x00" * 32


def get_keccak(data: bytes | None = None) -> sha3_256:
    return sha3_256(data=data, keccak=True)


def keccak_2hash(inp: bytes, buff: bytes | None = None) -> bytes:
    buff = buff if buff else bytearray(32)
    tcry.fast_hash_into(buff, inp)
    tcry.fast_hash_into(buff, buff)
    return buff


def compute_hmac(key: bytes, msg: bytes) -> bytes:
    digestmod = get_keccak
    inner = digestmod()
    block_size = inner.block_size
    if len(key) > block_size:
        key = digestmod(key).digest()
    key_block = bytearray(block_size)
    for i in range(block_size):
        key_block[i] = 0x36
    for i in range(len(key)):
        key_block[i] ^= key[i]
    inner.update(key_block)
    inner.update(msg)
    outer = digestmod()
    for i in range(block_size):
        key_block[i] = 0x5C
    for i in range(len(key)):
        key_block[i] ^= key[i]
    outer.update(key_block)
    outer.update(inner.digest())
    return outer.digest()


#
# EC
#


def decodepoint(x: bytes) -> tcry.Point:
    return tcry.decodepoint_into(None, x)


def encodepoint(x: tcry.Point, offset: int = 0) -> bytes:
    return tcry.encodepoint_into(None, x, offset)


def encodeint(x: tcry.Scalar, offset: int = 0) -> bytes:
    return tcry.encodeint_into(None, x, offset)


def decodeint(x: bytes) -> tcry.Scalar:
    return tcry.decodeint_into(None, x)


INV_EIGHT = b"\x79\x2f\xdc\xe2\x29\xe5\x06\x61\xd0\xda\x1c\x7d\xb3\x9d\xd3\x07\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x06"
INV_EIGHT_SC = decodeint(INV_EIGHT)


def generate_key_derivation(pub: tcry.Point, sec: tcry.Scalar) -> tcry.Point:
    """
    Key derivation: 8*(key2*key1)
    """
    tcry.sc_check(sec)  # checks that the secret key is uniform enough...
    tcry.ge25519_check(pub)
    return tcry.xmr_generate_key_derivation(None, pub, sec)


def derivation_to_scalar(derivation: tcry.Point, output_index: int) -> tcry.Scalar:
    """
    H_s(derivation || varint(output_index))
    """
    tcry.ge25519_check(derivation)
    return tcry.xmr_derivation_to_scalar(None, derivation, output_index)


def derive_public_key(
    derivation: tcry.Point, output_index: int, B: tcry.Point
) -> tcry.Point:
    """
    H_s(derivation || varint(output_index))G + B
    """
    tcry.ge25519_check(B)
    return tcry.xmr_derive_public_key(None, derivation, output_index, B)


def derive_secret_key(
    derivation: tcry.Point, output_index: int, base: tcry.Scalar
) -> tcry.Scalar:
    """
    base + H_s(derivation || varint(output_index))
    """
    tcry.sc_check(base)
    return tcry.xmr_derive_private_key(None, derivation, output_index, base)


def get_subaddress_secret_key(
    secret_key: tcry.Scalar, major: int = 0, minor: int = 0
) -> tcry.Scalar:
    """
    Builds subaddress secret key from the subaddress index
    Hs(SubAddr || a || index_major || index_minor)
    """
    return tcry.xmr_get_subaddress_secret_key(None, major, minor, secret_key)


def xor8(buff: bytearray, key: bytes) -> bytes:
    for i in range(8):
        buff[i] ^= key[i]
    return buff
