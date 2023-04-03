"""
Multilayer Linkable Spontaneous Anonymous Group (MLSAG)
Optimized versions with incremental hashing.

See https://eprint.iacr.org/2015/1098.pdf for details.
Also explained in From Zero to Monero section 3.3 and 5.

----------

Please note, that the MLSAG code is written in a generic manner,
where it is designed for multiple public keys (aka inputs). In another
words, MLSAG should be used to sign multiple inputs, but that is currently
not the case of Monero, where the inputs are signed one by one.
So the public keys matrix has always two rows (one for public keys,
one for commitments), although the algorithm is designed for `n` rows.

This has one unfortunate effect where `rows` is always equal to 2 and
dsRows always to 1, but the algorithm is still written as the numbers
are arbitrary. That's why there are loops such as `for i in range(dsRows)`
where it is run only once currently.

----------

Also note, that the matrix of public keys is indexed by columns first.
This is because the code was ported from the official Monero client,
which is written in C++ and where it does have some memory advantages.

For ring size = 3 and one input the matrix M will look like this:
|------------------------|------------------------|------------------------|
| public key 0           | public key 1           | public key 2           |
| cmt 0 - pseudo_out cmt | cmt 1 - pseudo_out cmt | cmt 2 - pseudo_out cmt |

and `sk` is equal to:
|--------------|-----------------------------------------------------|
| private key* | input secret key's mask - pseudo_out's mask (alpha) |

* corresponding to one of the public keys (`index` denotes which one)

----------

Mostly ported from official Monero client, but also inspired by Mininero.
Author: Dusan Klinec, ph4r05, 2018
"""

import gc
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any, TypeGuard, TypeVar

    from trezor.messages import MoneroRctKeyPublic

    from apps.monero.xmr import crypto

    from .serialize_messages.tx_ct_key import CtKey

    T = TypeVar("T")

    def _list_of_type(lst: list[Any], typ: type[T]) -> TypeGuard[list[T]]:
        ...


_HASH_KEY_CLSAG_ROUND = b"CLSAG_round\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
_HASH_KEY_CLSAG_AGG_0 = b"CLSAG_agg_0\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
_HASH_KEY_CLSAG_AGG_1 = b"CLSAG_agg_1\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"


def generate_clsag_simple(
    message: bytes,
    pubs: list[MoneroRctKeyPublic],
    in_sk: CtKey,
    a: crypto.Scalar,
    cout: crypto.Point,
    index: int,
    mg_buff: list[bytearray],
) -> list[bytes]:
    """
    CLSAG for RctType.Simple
    https://eprint.iacr.org/2019/654.pdf

    Corresponds to proveRctCLSAGSimple in rctSigs.cpp

    :param message: the full message to be signed (actually its hash)
    :param pubs: vector of MoneroRctKey; this forms the ring; point values in encoded form; (dest, mask) = (P, C)
    :param in_sk: CtKey; spending private key with input commitment mask (original); better_name: input_secret_key
    :param a: mask from the pseudo output commitment; better name: pseudo_out_alpha
    :param cout: pseudo output commitment; point, decoded; better name: pseudo_out_c
    :param index: specifies corresponding public key to the `in_sk` in the pubs array
    :param mg_buff: buffer to store the signature to
    """
    from apps.monero.xmr import crypto

    cols = len(pubs)
    if cols == 0:
        raise ValueError("Empty pubs")

    P = _key_vector(cols)
    C_nonzero = _key_vector(cols)
    p = in_sk.dest
    z = crypto.sc_sub_into(None, in_sk.mask, a)

    for i in range(cols):
        P[i] = pubs[i].dest
        C_nonzero[i] = pubs[i].commitment
        pubs[i] = None  # type: ignore

    del pubs
    gc.collect()

    return _generate_clsag(message, P, p, C_nonzero, z, cout, index, mg_buff)


def _generate_clsag(
    message: bytes,
    P: list[bytes],
    p: crypto.Scalar,
    C_nonzero: list[bytes],
    z: crypto.Scalar,
    Cout: crypto.Point,
    index: int,
    mg_buff: list[bytearray],
) -> list[bytes]:
    from apps.monero.xmr import crypto, crypto_helpers
    from apps.monero.xmr.serialize import int_serialize

    Point = crypto.Point  # local_cache_attribute
    Scalar = crypto.Scalar  # local_cache_attribute
    encodepoint_into = crypto.encodepoint_into  # local_cache_attribute
    sc_mul_into = crypto.sc_mul_into  # local_cache_attribute
    scalarmult_into = crypto.scalarmult_into  # local_cache_attribute

    sI = Point()  # sig.I
    sD = Point()  # sig.D
    sc1 = Scalar()  # sig.c1
    a = crypto.random_scalar()
    H = Point()
    D = Point()
    Cout_bf = crypto_helpers.encodepoint(Cout)

    tmp_sc = Scalar()
    tmp = Point()
    tmp_bf = bytearray(32)

    crypto.hash_to_point_into(H, P[index])
    scalarmult_into(sI, H, p)  # I = p*H
    scalarmult_into(D, H, z)  # D = z*H
    sc_mul_into(tmp_sc, z, crypto_helpers.INV_EIGHT_SC)  # 1/8*z
    scalarmult_into(sD, H, tmp_sc)  # sig.D = 1/8*z*H
    sD = crypto_helpers.encodepoint(sD)

    hsh_P = crypto_helpers.get_keccak()  # domain, I, D, P, C, C_offset
    hsh_C = crypto_helpers.get_keccak()  # domain, I, D, P, C, C_offset
    hsh_P.update(_HASH_KEY_CLSAG_AGG_0)
    hsh_C.update(_HASH_KEY_CLSAG_AGG_1)

    def hsh_PC(x):
        nonlocal hsh_P, hsh_C
        hsh_P.update(x)
        hsh_C.update(x)

    for x in P:
        hsh_PC(x)

    for x in C_nonzero:
        hsh_PC(x)

    hsh_PC(encodepoint_into(tmp_bf, sI))
    hsh_PC(sD)
    hsh_PC(Cout_bf)
    mu_P = crypto_helpers.decodeint(hsh_P.digest())
    mu_C = crypto_helpers.decodeint(hsh_C.digest())

    del (hsh_PC, hsh_P, hsh_C)
    c_to_hash = crypto_helpers.get_keccak()  # domain, P, C, C_offset, message, aG, aH
    update = c_to_hash.update  # local_cache_attribute
    update(_HASH_KEY_CLSAG_ROUND)
    for i in range(len(P)):
        update(P[i])
    for i in range(len(P)):
        update(C_nonzero[i])
    update(Cout_bf)
    update(message)

    chasher = c_to_hash.copy()
    crypto.scalarmult_base_into(tmp, a)
    chasher.update(encodepoint_into(tmp_bf, tmp))  # aG
    scalarmult_into(tmp, H, a)
    chasher.update(encodepoint_into(tmp_bf, tmp))  # aH
    c = crypto_helpers.decodeint(chasher.digest())
    del (chasher, H)

    L = Point()
    R = Point()
    c_p = Scalar()
    c_c = Scalar()
    i = (index + 1) % len(P)
    if i == 0:
        crypto.sc_copy(sc1, c)

    mg_buff.append(int_serialize.dump_uvarint_b(len(P)))
    for _ in range(len(P)):
        mg_buff.append(bytearray(32))

    while i != index:
        crypto.random_scalar(tmp_sc)
        crypto.encodeint_into(mg_buff[i + 1], tmp_sc)

        sc_mul_into(c_p, mu_P, c)
        sc_mul_into(c_c, mu_C, c)

        # L = tmp_sc * G + c_P * P[i] + c_c * C[i]
        crypto.add_keys2_into(L, tmp_sc, c_p, crypto.decodepoint_into(tmp, P[i]))
        crypto.decodepoint_into(tmp, C_nonzero[i])  # C = C_nonzero - Cout
        crypto.point_sub_into(tmp, tmp, Cout)
        scalarmult_into(tmp, tmp, c_c)
        crypto.point_add_into(L, L, tmp)

        # R = tmp_sc * HP + c_p * I + c_c * D
        crypto.hash_to_point_into(tmp, P[i])
        crypto.add_keys3_into(R, tmp_sc, tmp, c_p, sI)
        crypto.point_add_into(R, R, scalarmult_into(tmp, D, c_c))

        chasher = c_to_hash.copy()
        chasher.update(encodepoint_into(tmp_bf, L))
        chasher.update(encodepoint_into(tmp_bf, R))
        crypto.decodeint_into(c, chasher.digest())

        P[i] = None  # type: ignore
        C_nonzero[i] = None  # type: ignore

        i = (i + 1) % len(P)
        if i == 0:
            crypto.sc_copy(sc1, c)

        if i & 3 == 0:
            gc.collect()

    # Final scalar = a - c * (mu_P * p + mu_c * Z)
    sc_mul_into(tmp_sc, mu_P, p)
    crypto.sc_muladd_into(tmp_sc, mu_C, z, tmp_sc)
    crypto.sc_mulsub_into(tmp_sc, c, tmp_sc, a)
    crypto.encodeint_into(mg_buff[index + 1], tmp_sc)

    if TYPE_CHECKING:
        assert _list_of_type(mg_buff, bytes)

    mg_buff.append(crypto_helpers.encodeint(sc1))
    mg_buff.append(sD)
    return mg_buff


def _key_vector(rows: int) -> list[Any]:
    return [None] * rows
