"""
Multilayer Linkable Spontaneous Anonymous Group (MLSAG)
Optimized versions with incremental hashing.
Both Simple and Full Monero tx types are supported.

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
from apps.monero.xmr import crypto


def generate_mlsag_full(
    message, pubs, in_sk, out_sk_mask, out_pk_commitments, kLRki, index, txn_fee_key
):
    cols = len(pubs)
    if cols == 0:
        raise ValueError("Empty pubs")
    rows = len(pubs[0])
    if rows == 0:
        raise ValueError("Empty pub row")
    for i in range(cols):
        if len(pubs[i]) != rows:
            raise ValueError("pub is not rectangular")

    if len(in_sk) != rows:
        raise ValueError("Bad inSk size")
    if len(out_sk_mask) != len(out_pk_commitments):
        raise ValueError("Bad outsk/putpk size")

    sk = _key_vector(rows + 1)
    M = _key_matrix(rows + 1, cols)
    for i in range(rows + 1):
        sk[i] = crypto.sc_0()

    for i in range(cols):
        M[i][rows] = crypto.identity()
        for j in range(rows):
            M[i][j] = crypto.decodepoint(pubs[i][j].dest)
            M[i][rows] = crypto.point_add(
                M[i][rows], crypto.decodepoint(pubs[i][j].commitment)
            )

    sk[rows] = crypto.sc_0()
    for j in range(rows):
        sk[j] = in_sk[j].dest
        sk[rows] = crypto.sc_add(sk[rows], in_sk[j].mask)  # add masks in last row

    for i in range(cols):
        for j in range(len(out_pk_commitments)):
            M[i][rows] = crypto.point_sub(
                M[i][rows], crypto.decodepoint(out_pk_commitments[j])
            )  # subtract output Ci's in last row

        # Subtract txn fee output in last row
        M[i][rows] = crypto.point_sub(M[i][rows], txn_fee_key)

    for j in range(len(out_pk_commitments)):
        sk[rows] = crypto.sc_sub(
            sk[rows], out_sk_mask[j]
        )  # subtract output masks in last row

    return generate_mlsag(message, M, sk, kLRki, index, rows)


def generate_mlsag_simple(message, pubs, in_sk, a, cout, kLRki, index):
    """
    MLSAG for RctType.Simple
    :param message: the full message to be signed (actually its hash)
    :param pubs: vector of MoneroRctKey; this forms the ring; point values in encoded form; (dest, mask) = (P, C)
    :param in_sk: CtKey; spending private key with input commitment mask (original); better_name: input_secret_key
    :param a: mask from the pseudo output commitment; better name: pseudo_out_alpha
    :param cout: pseudo output commitment; point, decoded; better name: pseudo_out_c
    :param kLRki: used only in multisig, currently not implemented
    :param index: specifies corresponding public key to the `in_sk` in the pubs array
    :return: MgSig
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

    for i in range(cols):
        M[i][0] = crypto.decodepoint(pubs[i].dest)
        M[i][1] = crypto.point_sub(crypto.decodepoint(pubs[i].commitment), cout)

    return generate_mlsag(message, M, sk, kLRki, index, dsRows)


def gen_mlsag_assert(pk, xx, kLRki, index, dsRows):
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
    if kLRki and dsRows != 1:
        raise ValueError("Multisig requires exactly 1 dsRows")
    if kLRki:
        raise NotImplementedError("Multisig not implemented")
    return rows, cols


def generate_first_c_and_key_images(
    message, rv, pk, xx, kLRki, index, dsRows, rows, cols
):
    """
    MLSAG computation - the part with secret keys
    :param message: the full message to be signed (actually its hash)
    :param rv: MgSig
    :param pk: matrix of public keys and commitments
    :param xx: input secret array composed of a private key and commitment mask
    :param kLRki: used only in multisig, currently not implemented
    :param index: specifies corresponding public key to the `xx`'s private key in the `pk` array
    :param dsRows: row number where the pubkeys "end" (and commitments follow)
    :param rows: total number of rows
    :param cols: size of ring
    """
    Ip = _key_vector(dsRows)
    rv.II = _key_vector(dsRows)
    alpha = _key_vector(rows)
    rv.ss = _key_matrix(rows, cols)

    tmp_buff = bytearray(32)
    hasher = _hasher_message(message)

    for i in range(dsRows):
        # this is somewhat extra as compared to the Ring Confidential Tx paper
        # see footnote in From Zero to Monero section 3.3
        hasher.update(crypto.encodepoint(pk[index][i]))
        if kLRki:
            raise NotImplementedError("Multisig not implemented")
            # alpha[i] = kLRki.k
            # rv.II[i] = kLRki.ki
            # hash_point(hasher, kLRki.L, tmp_buff)
            # hash_point(hasher, kLRki.R, tmp_buff)

        else:
            Hi = crypto.hash_to_point(crypto.encodepoint(pk[index][i]))
            alpha[i] = crypto.random_scalar()
            # L = alpha_i * G
            aGi = crypto.scalarmult_base(alpha[i])
            # Ri = alpha_i * H(P_i)
            aHPi = crypto.scalarmult(Hi, alpha[i])
            # key image
            rv.II[i] = crypto.scalarmult(Hi, xx[i])
            _hash_point(hasher, aGi, tmp_buff)
            _hash_point(hasher, aHPi, tmp_buff)

        Ip[i] = rv.II[i]

    for i in range(dsRows, rows):
        alpha[i] = crypto.random_scalar()
        # L = alpha_i * G
        aGi = crypto.scalarmult_base(alpha[i])
        # for some reasons we omit calculating R here, which seems
        # contrary to the paper, but it is in the Monero official client
        # see https://github.com/monero-project/monero/blob/636153b2050aa0642ba86842c69ac55a5d81618d/src/ringct/rctSigs.cpp#L191
        _hash_point(hasher, pk[index][i], tmp_buff)
        _hash_point(hasher, aGi, tmp_buff)

    # the first c
    c_old = hasher.digest()
    c_old = crypto.decodeint(c_old)
    return c_old, Ip, alpha


def generate_mlsag(message, pk, xx, kLRki, index, dsRows):
    """
    Multilayered Spontaneous Anonymous Group Signatures (MLSAG signatures)

    :param message: the full message to be signed (actually its hash)
    :param pk: matrix of public keys and commitments
    :param xx: input secret array composed of a private key and commitment mask
    :param kLRki: used only in multisig, currently not implemented
    :param index: specifies corresponding public key to the `xx`'s private key in the `pk` array
    :param dsRows: separates pubkeys from commitment
    :return MgSig
    """
    from apps.monero.xmr.serialize_messages.tx_full import MgSig

    rows, cols = gen_mlsag_assert(pk, xx, kLRki, index, dsRows)

    rv = MgSig()
    c, L, R, Hi = 0, None, None, None

    # calculates the "first" c, key images and random scalars alpha
    c_old, Ip, alpha = generate_first_c_and_key_images(
        message, rv, pk, xx, kLRki, index, dsRows, rows, cols
    )

    i = (index + 1) % cols
    if i == 0:
        rv.cc = c_old

    tmp_buff = bytearray(32)
    while i != index:
        rv.ss[i] = _generate_random_vector(rows)
        hasher = _hasher_message(message)

        for j in range(dsRows):
            # L = rv.ss[i][j] * G + c_old * pk[i][j]
            L = crypto.add_keys2(rv.ss[i][j], c_old, pk[i][j])
            Hi = crypto.hash_to_point(crypto.encodepoint(pk[i][j]))
            # R = rv.ss[i][j] * H(pk[i][j]) + c_old * Ip[j]
            R = crypto.add_keys3(rv.ss[i][j], Hi, c_old, rv.II[j])
            _hash_point(hasher, pk[i][j], tmp_buff)
            _hash_point(hasher, L, tmp_buff)
            _hash_point(hasher, R, tmp_buff)

        for j in range(dsRows, rows):
            # again, omitting R here as discussed above
            L = crypto.add_keys2(rv.ss[i][j], c_old, pk[i][j])
            _hash_point(hasher, pk[i][j], tmp_buff)
            _hash_point(hasher, L, tmp_buff)

        c = crypto.decodeint(hasher.digest())
        c_old = c
        i = (i + 1) % cols

        if i == 0:
            rv.cc = c_old

    for j in range(rows):
        rv.ss[index][j] = crypto.sc_mulsub(c, xx[j], alpha[j])

    return rv


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


def _generate_random_vector(n):
    """
    Generates vector of random scalars
    """
    return [crypto.random_scalar() for _ in range(0, n)]


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
