# Author: Dusan Klinec, ph4r05, 2018
#
# Resources:
# https://cr.yp.to
# https://github.com/monero-project/mininero
# https://godoc.org/github.com/agl/ed25519/edwards25519
# https://tools.ietf.org/html/draft-josefsson-eddsa-ed25519-00#section-4
# https://github.com/monero-project/research-lab

from trezor.crypto import hmac, monero as tcry, random
from trezor.crypto.hashlib import sha3_256

if False:
    from typing import Tuple, Optional, Union
    from apps.monero.xmr.types import Sc25519, Ge25519


NULL_KEY_ENC = b"\x00" * 32

random_bytes = random.bytes
ct_equals = tcry.ct_equals


def keccak_factory(data=None):
    return sha3_256(data=data, keccak=True)


get_keccak = keccak_factory
keccak_hash = tcry.xmr_fast_hash
keccak_hash_into = tcry.xmr_fast_hash


def keccak_2hash(inp, buff=None):
    buff = buff if buff else bytearray(32)
    keccak_hash_into(buff, inp)
    keccak_hash_into(buff, buff)
    return buff


def compute_hmac(key, msg=None):
    h = hmac.new(key, msg=msg, digestmod=keccak_factory)
    return h.digest()


#
# EC
#


new_point = tcry.ge25519_set_neutral


def new_scalar() -> Sc25519:
    return tcry.init256_modm(0)


decodepoint = tcry.ge25519_unpack_vartime
decodepoint_into = tcry.ge25519_unpack_vartime
encodepoint = tcry.ge25519_pack
encodepoint_into = tcry.ge25519_pack

decodeint = tcry.unpack256_modm
decodeint_into_noreduce = tcry.unpack256_modm_noreduce
decodeint_into = tcry.unpack256_modm
encodeint = tcry.pack256_modm
encodeint_into = tcry.pack256_modm

check_ed25519point = tcry.ge25519_check

scalarmult_base = tcry.ge25519_scalarmult_base
scalarmult_base_into = tcry.ge25519_scalarmult_base
scalarmult = tcry.ge25519_scalarmult
scalarmult_into = tcry.ge25519_scalarmult

point_add = tcry.ge25519_add
point_add_into = tcry.ge25519_add
point_sub = tcry.ge25519_sub
point_sub_into = tcry.ge25519_sub
point_eq = tcry.ge25519_eq
point_double = tcry.ge25519_double
point_double_into = tcry.ge25519_double
point_mul8 = tcry.ge25519_mul8
point_mul8_into = tcry.ge25519_mul8

INV_EIGHT = b"\x79\x2f\xdc\xe2\x29\xe5\x06\x61\xd0\xda\x1c\x7d\xb3\x9d\xd3\x07\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x06"
INV_EIGHT_SC = decodeint(INV_EIGHT)


def sc_inv_eight() -> Sc25519:
    return INV_EIGHT_SC


#
# Zmod(order), scalar values field
#


def sc_0() -> Sc25519:
    return tcry.init256_modm(0)


def sc_0_into(r: Sc25519) -> Sc25519:
    return tcry.init256_modm(r, 0)


def sc_init(x: int) -> Sc25519:
    if x >= (1 << 64):
        raise ValueError("Initialization works up to 64-bit only")
    return tcry.init256_modm(x)


def sc_init_into(r: Sc25519, x: int) -> Sc25519:
    if x >= (1 << 64):
        raise ValueError("Initialization works up to 64-bit only")
    return tcry.init256_modm(r, x)


sc_copy = tcry.init256_modm
sc_get64 = tcry.get256_modm
sc_check = tcry.check256_modm
check_sc = tcry.check256_modm

sc_add = tcry.add256_modm
sc_add_into = tcry.add256_modm
sc_sub = tcry.sub256_modm
sc_sub_into = tcry.sub256_modm
sc_mul = tcry.mul256_modm
sc_mul_into = tcry.mul256_modm


def sc_isnonzero(c: Sc25519) -> bool:
    """
    Returns true if scalar is non-zero
    """
    return not tcry.iszero256_modm(c)


sc_eq = tcry.eq256_modm
sc_mulsub = tcry.mulsub256_modm
sc_mulsub_into = tcry.mulsub256_modm
sc_muladd = tcry.muladd256_modm
sc_muladd_into = tcry.muladd256_modm
sc_inv_into = tcry.inv256_modm


def random_scalar(r=None) -> Sc25519:
    return tcry.xmr_random_scalar(r if r is not None else new_scalar())


#
# GE - ed25519 group
#


def ge25519_double_scalarmult_base_vartime(a, A, b) -> Ge25519:
    """
    void ge25519_double_scalarmult_vartime(ge25519 *r, const ge25519 *p1, const bignum256modm s1, const bignum256modm s2);
    r = a * A + b * B
    """
    R = tcry.ge25519_double_scalarmult_vartime(A, a, b)
    return R


ge25519_double_scalarmult_vartime2 = tcry.xmr_add_keys3


def identity(byte_enc=False) -> Union[Ge25519, bytes]:
    idd = tcry.ge25519_set_neutral()
    return idd if not byte_enc else encodepoint(idd)


identity_into = tcry.ge25519_set_neutral

"""
https://www.imperialviolet.org/2013/12/25/elligator.html
http://elligator.cr.yp.to/
http://elligator.cr.yp.to/elligator-20130828.pdf
"""

#
# Monero specific
#


cn_fast_hash = keccak_hash


def hash_to_scalar(data: bytes, length: Optional[int] = None):
    """
    H_s(P)
    """
    dt = data[:length] if length else data
    return tcry.xmr_hash_to_scalar(dt)


def hash_to_scalar_into(r: Sc25519, data: bytes, length: Optional[int] = None):
    dt = data[:length] if length else data
    return tcry.xmr_hash_to_scalar(r, dt)


"""
H_p(buf)

Code adapted from MiniNero: https://github.com/monero-project/mininero
https://github.com/monero-project/research-lab/blob/master/whitepaper/ge_fromfe_writeup/ge_fromfe.pdf
http://archive.is/yfINb
"""
hash_to_point = tcry.xmr_hash_to_ec
hash_to_point_into = tcry.xmr_hash_to_ec


#
# XMR
#


xmr_H = tcry.ge25519_set_h


def scalarmult_h(i) -> Ge25519:
    return scalarmult(xmr_H(), sc_init(i) if isinstance(i, int) else i)


add_keys2 = tcry.xmr_add_keys2_vartime
add_keys2_into = tcry.xmr_add_keys2_vartime
add_keys3 = tcry.xmr_add_keys3_vartime
add_keys3_into = tcry.xmr_add_keys3_vartime
gen_commitment = tcry.xmr_gen_c


def generate_key_derivation(pub: Ge25519, sec: Sc25519) -> Ge25519:
    """
    Key derivation: 8*(key2*key1)
    """
    sc_check(sec)  # checks that the secret key is uniform enough...
    check_ed25519point(pub)
    return tcry.xmr_generate_key_derivation(pub, sec)


def derivation_to_scalar(derivation: Ge25519, output_index: int) -> Sc25519:
    """
    H_s(derivation || varint(output_index))
    """
    check_ed25519point(derivation)
    return tcry.xmr_derivation_to_scalar(derivation, output_index)


def derive_public_key(derivation: Ge25519, output_index: int, B: Ge25519) -> Ge25519:
    """
    H_s(derivation || varint(output_index))G + B
    """
    check_ed25519point(B)
    return tcry.xmr_derive_public_key(derivation, output_index, B)


def derive_secret_key(derivation: Ge25519, output_index: int, base: Sc25519) -> Sc25519:
    """
    base + H_s(derivation || varint(output_index))
    """
    sc_check(base)
    return tcry.xmr_derive_private_key(derivation, output_index, base)


def get_subaddress_secret_key(
    secret_key: Sc25519, major: int = 0, minor: int = 0
) -> Sc25519:
    """
    Builds subaddress secret key from the subaddress index
    Hs(SubAddr || a || index_major || index_minor)
    """
    return tcry.xmr_get_subaddress_secret_key(major, minor, secret_key)


def generate_signature(data: bytes, priv: Sc25519) -> Tuple[Sc25519, Sc25519, Ge25519]:
    """
    Generate EC signature
    crypto_ops::generate_signature(const hash &prefix_hash, const public_key &pub, const secret_key &sec, signature &sig)
    """
    pub = scalarmult_base(priv)

    k = random_scalar()
    comm = scalarmult_base(k)

    buff = data + encodepoint(pub) + encodepoint(comm)
    c = hash_to_scalar(buff)
    r = sc_mulsub(priv, c, k)
    return c, r, pub


def check_signature(data: bytes, c: Sc25519, r: Sc25519, pub: Ge25519) -> bool:
    """
    EC signature verification
    """
    check_ed25519point(pub)
    if sc_check(c) != 0 or sc_check(r) != 0:
        raise ValueError("Signature error")

    tmp2 = point_add(scalarmult(pub, c), scalarmult_base(r))
    buff = data + encodepoint(pub) + encodepoint(tmp2)
    tmp_c = hash_to_scalar(buff)
    res = sc_sub(tmp_c, c)
    return not sc_isnonzero(res)


def xor8(buff: bytes, key: bytes) -> bytes:
    for i in range(8):
        buff[i] ^= key[i]
    return buff
