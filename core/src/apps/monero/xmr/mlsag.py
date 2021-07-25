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

from apps.monero.xmr import crypto
from apps.monero.xmr.serialize import int_serialize

if False:
    from apps.monero.xmr.types import Ge25519, Sc25519
    from apps.monero.xmr.serialize_messages.tx_ct_key import CtKey
    from trezor.messages import MoneroRctKeyPublic

    KeyM = list[list[bytes]]


_HASH_KEY_CLSAG_ROUND = b"CLSAG_round\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
_HASH_KEY_CLSAG_AGG_0 = b"CLSAG_agg_0\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
_HASH_KEY_CLSAG_AGG_1 = b"CLSAG_agg_1\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"


def generate_mlsag_simple(
    message: bytes,
    pubs: list[MoneroRctKeyPublic],
    in_sk: CtKey,
    a: Sc25519,
    cout: Ge25519,
    index: int,
    mg_buff: list[bytes],
) -> list[bytes]:
    """
    MLSAG for RctType.Simple
    :param message: the full message to be signed (actually its hash)
    :param pubs: vector of MoneroRctKey; this forms the ring; point values in encoded form; (dest, mask) = (P, C)
    :param in_sk: CtKey; spending private key with input commitment mask (original); better_name: input_secret_key
    :param a: mask from the pseudo output commitment; better name: pseudo_out_alpha
    :param cout: pseudo output commitment; point, decoded; better name: pseudo_out_c
    :param index: specifies corresponding public key to the `in_sk` in the pubs array
    :param mg_buff: buffer to store the signature to
    """
    # Monero signs inputs separately, so `rows` always equals 2 (pubkey, commitment)
    # and `dsRows` is always 1 (denotes where the pubkeys "end")
    rows = 2
    dsRows = 1
    cols = len(pubs)
    if cols == 0:
        raise ValueError("Empty pubs")

    sk = _key_vector(rows)
    M = _key_matrix(rows, cols)

    sk[0] = in_sk.dest
    sk[1] = crypto.sc_sub(in_sk.mask, a)
    tmp_pt = crypto.new_point()

    for i in range(cols):
        crypto.point_sub_into(
            tmp_pt, crypto.decodepoint_into(tmp_pt, pubs[i].commitment), cout
        )

        M[i][0] = pubs[i].dest
        M[i][1] = crypto.encodepoint(tmp_pt)
        pubs[i] = None

    del pubs
    gc.collect()

    return generate_mlsag(message, M, sk, index, dsRows, mg_buff)


def gen_mlsag_assert(pk: KeyM, xx: list[Sc25519], index: int, dsRows: int):
    """
    Conditions check
    """
    cols = len(pk)
    if cols <= 1:
        raise ValueError("Cols == 1")
    if index >= cols:
        raise ValueError("Index out of range")

    rows = len(pk[0])
    if rows == 0:
        raise ValueError("Empty pk")

    for i in range(cols):
        if len(pk[i]) != rows:
            raise ValueError("pk is not rectangular")
    if len(xx) != rows:
        raise ValueError("Bad xx size")
    if dsRows > rows:
        raise ValueError("Bad dsRows size")
    return rows, cols


def generate_first_c_and_key_images(
    message: bytes,
    pk: KeyM,
    xx: list[Sc25519],
    index: int,
    dsRows: int,
    rows: int,
    cols: int,
) -> tuple[Sc25519, list[Ge25519], list[Ge25519]]:
    """
    MLSAG computation - the part with secret keys
    :param message: the full message to be signed (actually its hash)
    :param pk: matrix of public keys and commitments
    :param xx: input secret array composed of a private key and commitment mask
    :param index: specifies corresponding public key to the `xx`'s private key in the `pk` array
    :param dsRows: row number where the pubkeys "end" (and commitments follow)
    :param rows: total number of rows
    :param cols: size of ring
    """
    II = _key_vector(dsRows)
    alpha = _key_vector(rows)

    tmp_buff = bytearray(32)
    Hi = crypto.new_point()
    aGi = crypto.new_point()
    aHPi = crypto.new_point()
    hasher = _hasher_message(message)

    for i in range(dsRows):
        # this is somewhat extra as compared to the Ring Confidential Tx paper
        # see footnote in From Zero to Monero section 3.3
        hasher.update(pk[index][i])

        crypto.hash_to_point_into(Hi, pk[index][i])
        alpha[i] = crypto.random_scalar()
        # L = alpha_i * G
        crypto.scalarmult_base_into(aGi, alpha[i])
        # Ri = alpha_i * H(P_i)
        crypto.scalarmult_into(aHPi, Hi, alpha[i])
        # key image
        II[i] = crypto.scalarmult(Hi, xx[i])
        _hash_point(hasher, aGi, tmp_buff)
        _hash_point(hasher, aHPi, tmp_buff)

    for i in range(dsRows, rows):
        alpha[i] = crypto.random_scalar()
        # L = alpha_i * G
        crypto.scalarmult_base_into(aGi, alpha[i])
        # for some reasons we omit calculating R here, which seems
        # contrary to the paper, but it is in the Monero official client
        # see https://github.com/monero-project/monero/blob/636153b2050aa0642ba86842c69ac55a5d81618d/src/ringct/rctSigs.cpp#L191
        hasher.update(pk[index][i])
        _hash_point(hasher, aGi, tmp_buff)

    # the first c
    c_old = hasher.digest()
    c_old = crypto.decodeint(c_old)
    return c_old, II, alpha


def generate_mlsag(
    message: bytes,
    pk: KeyM,
    xx: list[Sc25519],
    index: int,
    dsRows: int,
    mg_buff: list[bytes],
) -> list[bytes]:
    """
    Multilayered Spontaneous Anonymous Group Signatures (MLSAG signatures)

    :param message: the full message to be signed (actually its hash)
    :param pk: matrix of public keys and commitments
    :param xx: input secret array composed of a private key and commitment mask
    :param index: specifies corresponding public key to the `xx`'s private key in the `pk` array
    :param dsRows: separates pubkeys from commitment
    :param mg_buff: mg signature buffer
    """
    rows, cols = gen_mlsag_assert(pk, xx, index, dsRows)
    rows_b_size = int_serialize.uvarint_size(rows)

    # Preallocation of the chunked buffer, len + cols + cc
    for _ in range(1 + cols + 1):
        mg_buff.append(None)

    mg_buff[0] = int_serialize.dump_uvarint_b(cols)
    cc = crypto.new_scalar()  # rv.cc
    c = crypto.new_scalar()
    L = crypto.new_point()
    R = crypto.new_point()
    Hi = crypto.new_point()

    # calculates the "first" c, key images and random scalars alpha
    c_old, II, alpha = generate_first_c_and_key_images(
        message, pk, xx, index, dsRows, rows, cols
    )

    i = (index + 1) % cols
    if i == 0:
        crypto.sc_copy(cc, c_old)

    ss = [crypto.new_scalar() for _ in range(rows)]
    tmp_buff = bytearray(32)

    while i != index:
        hasher = _hasher_message(message)

        # Serialize size of the row
        mg_buff[i + 1] = bytearray(rows_b_size + 32 * rows)
        int_serialize.dump_uvarint_b_into(rows, mg_buff[i + 1])

        for x in ss:
            crypto.random_scalar(x)

        for j in range(dsRows):
            # L = rv.ss[i][j] * G + c_old * pk[i][j]
            crypto.add_keys2_into(
                L, ss[j], c_old, crypto.decodepoint_into(Hi, pk[i][j])
            )
            crypto.hash_to_point_into(Hi, pk[i][j])

            # R = rv.ss[i][j] * H(pk[i][j]) + c_old * Ip[j]
            crypto.add_keys3_into(R, ss[j], Hi, c_old, II[j])

            hasher.update(pk[i][j])
            _hash_point(hasher, L, tmp_buff)
            _hash_point(hasher, R, tmp_buff)

        for j in range(dsRows, rows):
            # again, omitting R here as discussed above
            crypto.add_keys2_into(
                L, ss[j], c_old, crypto.decodepoint_into(Hi, pk[i][j])
            )
            hasher.update(pk[i][j])
            _hash_point(hasher, L, tmp_buff)

        for si in range(rows):
            crypto.encodeint_into(mg_buff[i + 1], ss[si], rows_b_size + 32 * si)

        crypto.decodeint_into(c, hasher.digest())
        crypto.sc_copy(c_old, c)
        pk[i] = None
        i = (i + 1) % cols

        if i == 0:
            crypto.sc_copy(cc, c_old)
        gc.collect()

    del II

    # Finalizing rv.ss by processing rv.ss[index]
    mg_buff[index + 1] = bytearray(rows_b_size + 32 * rows)
    int_serialize.dump_uvarint_b_into(rows, mg_buff[index + 1])
    for j in range(rows):
        crypto.sc_mulsub_into(ss[j], c, xx[j], alpha[j])
        crypto.encodeint_into(mg_buff[index + 1], ss[j], rows_b_size + 32 * j)

    # rv.cc
    mg_buff[-1] = crypto.encodeint(cc)
    return mg_buff


def generate_clsag_simple(
    message: bytes,
    pubs: list[MoneroRctKeyPublic],
    in_sk: CtKey,
    a: Sc25519,
    cout: Ge25519,
    index: int,
    mg_buff: list[bytes],
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
    cols = len(pubs)
    if cols == 0:
        raise ValueError("Empty pubs")

    P = _key_vector(cols)
    C_nonzero = _key_vector(cols)
    p = in_sk.dest
    z = crypto.sc_sub(in_sk.mask, a)

    for i in range(cols):
        P[i] = pubs[i].dest
        C_nonzero[i] = pubs[i].commitment
        pubs[i] = None

    del pubs
    gc.collect()

    return _generate_clsag(message, P, p, C_nonzero, z, cout, index, mg_buff)


def _generate_clsag(
    message: bytes,
    P: list[bytes],
    p: Sc25519,
    C_nonzero: list[bytes],
    z: Sc25519,
    Cout: Ge25519,
    index: int,
    mg_buff: list[bytes],
) -> list[bytes]:
    sI = crypto.new_point()  # sig.I
    sD = crypto.new_point()  # sig.D
    sc1 = crypto.new_scalar()  # sig.c1
    a = crypto.random_scalar()
    H = crypto.new_point()
    D = crypto.new_point()
    Cout_bf = crypto.encodepoint(Cout)

    tmp_sc = crypto.new_scalar()
    tmp = crypto.new_point()
    tmp_bf = bytearray(32)

    crypto.hash_to_point_into(H, P[index])
    crypto.scalarmult_into(sI, H, p)  # I = p*H
    crypto.scalarmult_into(D, H, z)  # D = z*H
    crypto.sc_mul_into(tmp_sc, z, crypto.sc_inv_eight())  # 1/8*z
    crypto.scalarmult_into(sD, H, tmp_sc)  # sig.D = 1/8*z*H
    sD = crypto.encodepoint(sD)

    hsh_P = crypto.get_keccak()  # domain, I, D, P, C, C_offset
    hsh_C = crypto.get_keccak()  # domain, I, D, P, C, C_offset
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

    hsh_PC(crypto.encodepoint_into(tmp_bf, sI))
    hsh_PC(sD)
    hsh_PC(Cout_bf)
    mu_P = crypto.decodeint(hsh_P.digest())
    mu_C = crypto.decodeint(hsh_C.digest())

    del (hsh_PC, hsh_P, hsh_C)
    c_to_hash = crypto.get_keccak()  # domain, P, C, C_offset, message, aG, aH
    c_to_hash.update(_HASH_KEY_CLSAG_ROUND)
    for i in range(len(P)):
        c_to_hash.update(P[i])
    for i in range(len(P)):
        c_to_hash.update(C_nonzero[i])
    c_to_hash.update(Cout_bf)
    c_to_hash.update(message)

    chasher = c_to_hash.copy()
    crypto.scalarmult_base_into(tmp, a)
    chasher.update(crypto.encodepoint_into(tmp_bf, tmp))  # aG
    crypto.scalarmult_into(tmp, H, a)
    chasher.update(crypto.encodepoint_into(tmp_bf, tmp))  # aH
    c = crypto.decodeint(chasher.digest())
    del (chasher, H)

    L = crypto.new_point()
    R = crypto.new_point()
    c_p = crypto.new_scalar()
    c_c = crypto.new_scalar()
    i = (index + 1) % len(P)
    if i == 0:
        crypto.sc_copy(sc1, c)

    mg_buff.append(int_serialize.dump_uvarint_b(len(P)))
    for _ in range(len(P)):
        mg_buff.append(bytearray(32))

    while i != index:
        crypto.random_scalar(tmp_sc)
        crypto.encodeint_into(mg_buff[i + 1], tmp_sc)

        crypto.sc_mul_into(c_p, mu_P, c)
        crypto.sc_mul_into(c_c, mu_C, c)

        # L = tmp_sc * G + c_P * P[i] + c_c * C[i]
        crypto.add_keys2_into(L, tmp_sc, c_p, crypto.decodepoint_into(tmp, P[i]))
        crypto.decodepoint_into(tmp, C_nonzero[i])  # C = C_nonzero - Cout
        crypto.point_sub_into(tmp, tmp, Cout)
        crypto.scalarmult_into(tmp, tmp, c_c)
        crypto.point_add_into(L, L, tmp)

        # R = tmp_sc * HP + c_p * I + c_c * D
        crypto.hash_to_point_into(tmp, P[i])
        crypto.add_keys3_into(R, tmp_sc, tmp, c_p, sI)
        crypto.point_add_into(R, R, crypto.scalarmult_into(tmp, D, c_c))

        chasher = c_to_hash.copy()
        chasher.update(crypto.encodepoint_into(tmp_bf, L))
        chasher.update(crypto.encodepoint_into(tmp_bf, R))
        crypto.decodeint_into(c, chasher.digest())

        P[i] = None
        C_nonzero[i] = None

        i = (i + 1) % len(P)
        if i == 0:
            crypto.sc_copy(sc1, c)

        if i & 3 == 0:
            gc.collect()

    # Final scalar = a - c * (mu_P * p + mu_c * Z)
    crypto.sc_mul_into(tmp_sc, mu_P, p)
    crypto.sc_muladd_into(tmp_sc, mu_C, z, tmp_sc)
    crypto.sc_mulsub_into(tmp_sc, c, tmp_sc, a)
    crypto.encodeint_into(mg_buff[index + 1], tmp_sc)

    mg_buff.append(crypto.encodeint(sc1))
    mg_buff.append(sD)
    return mg_buff


def _key_vector(rows):
    return [None] * rows


def _key_matrix(rows, cols):
    """
    first index is columns (so slightly backward from math)
    """
    rv = [None] * cols
    for i in range(0, cols):
        rv[i] = _key_vector(rows)
    return rv


def _hasher_message(message):
    """
    Returns incremental hasher for MLSAG
    """
    ctx = crypto.get_keccak()
    ctx.update(message)
    return ctx


def _hash_point(hasher, point, tmp_buff):
    crypto.encodepoint_into(tmp_buff, point)
    hasher.update(tmp_buff)
