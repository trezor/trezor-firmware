from trezor import utils

from apps.monero.xmr import crypto


def _build_key(secret, discriminator=None, index: int = None) -> bytes:
    """
    Creates an unique-purpose key
    """
    key_buff = bytearray(32 + 12 + 4)  # key + disc + index
    offset = 32
    utils.memcpy(key_buff, 0, secret, 0, len(secret))

    if discriminator is not None:
        utils.memcpy(key_buff, offset, discriminator, 0, len(discriminator))
        offset += len(discriminator)

    if index is not None:
        # dump_uvarint_b_into, saving import
        shifted = True
        while shifted:
            shifted = index >> 7
            key_buff[offset] = (index & 0x7F) | (0x80 if shifted else 0x00)
            offset += 1
            index = shifted

    return crypto.keccak_2hash(key_buff)


def hmac_key_txin(key_hmac, idx: int) -> bytes:
    """
    (TxSourceEntry[i] || tx.vin[i]) hmac key
    """
    return _build_key(key_hmac, b"txin", idx)


def hmac_key_txin_comm(key_hmac, idx: int) -> bytes:
    """
    pseudo_outputs[i] hmac key. Pedersen commitment for inputs.
    """
    return _build_key(key_hmac, b"txin-comm", idx)


def hmac_key_txdst(key_hmac, idx: int) -> bytes:
    """
    TxDestinationEntry[i] hmac key
    """
    return _build_key(key_hmac, b"txdest", idx)


def hmac_key_txout(key_hmac, idx: int) -> bytes:
    """
    (TxDestinationEntry[i] || tx.vout[i]) hmac key
    """
    return _build_key(key_hmac, b"txout", idx)


def hmac_key_txout_asig(key_hmac, idx: int) -> bytes:
    """
    rsig[i] hmac key. Range signature HMAC
    """
    return _build_key(key_hmac, b"txout-asig", idx)


def enc_key_txin_alpha(key_enc, idx: int) -> bytes:
    """
    Chacha20Poly1305 encryption key for alpha[i] used in Pedersen commitment in pseudo_outs[i]
    """
    return _build_key(key_enc, b"txin-alpha", idx)


def enc_key_spend(key_enc, idx: int) -> bytes:
    """
    Chacha20Poly1305 encryption key for alpha[i] used in Pedersen commitment in pseudo_outs[i]
    """
    return _build_key(key_enc, b"txin-spend", idx)


def enc_key_cout(key_enc, idx: int = None) -> bytes:
    """
    Chacha20Poly1305 encryption key for multisig C values from MLASG.
    """
    return _build_key(key_enc, b"cout", idx)


async def gen_hmac_vini(key, src_entr, vini_bin, idx: int) -> bytes:
    """
    Computes hmac (TxSourceEntry[i] || tx.vin[i])
    """
    import protobuf
    from apps.monero.xmr.keccak_hasher import get_keccak_writer

    kwriter = get_keccak_writer()
    await protobuf.dump_message(kwriter, src_entr)
    kwriter.write(vini_bin)

    hmac_key_vini = hmac_key_txin(key, idx)
    hmac_vini = crypto.compute_hmac(hmac_key_vini, kwriter.get_digest())
    return hmac_vini


async def gen_hmac_vouti(key, dst_entr, tx_out_bin, idx: int) -> bytes:
    """
    Generates HMAC for (TxDestinationEntry[i] || tx.vout[i])
    """
    import protobuf
    from apps.monero.xmr.keccak_hasher import get_keccak_writer

    kwriter = get_keccak_writer()
    await protobuf.dump_message(kwriter, dst_entr)
    kwriter.write(tx_out_bin)

    hmac_key_vouti = hmac_key_txout(key, idx)
    hmac_vouti = crypto.compute_hmac(hmac_key_vouti, kwriter.get_digest())
    return hmac_vouti


async def gen_hmac_tsxdest(key, dst_entr, idx: int) -> bytes:
    """
    Generates HMAC for TxDestinationEntry[i]
    """
    import protobuf
    from apps.monero.xmr.keccak_hasher import get_keccak_writer

    kwriter = get_keccak_writer()
    await protobuf.dump_message(kwriter, dst_entr)

    hmac_key = hmac_key_txdst(key, idx)
    hmac_tsxdest = crypto.compute_hmac(hmac_key, kwriter.get_digest())
    return hmac_tsxdest
