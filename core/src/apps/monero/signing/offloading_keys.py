from micropython import const

from trezor import utils

from apps.monero.xmr import crypto

if False:
    from apps.monero.xmr.types import Sc25519
    from trezor.messages import (
        MoneroTransactionDestinationEntry,
        MoneroTransactionSourceEntry,
    )


_SECRET_LENGTH = const(32)
_DISCRIMINATOR_LENGTH = const(12)
_INDEX_LENGTH = const(4)
_BUILD_KEY_BUFFER = bytearray(_SECRET_LENGTH + _DISCRIMINATOR_LENGTH + _INDEX_LENGTH)


def _build_key(
    secret, discriminator=None, index: int = None, out: bytes = None
) -> bytes:
    """
    Creates an unique-purpose key
    """

    key_buff = _BUILD_KEY_BUFFER
    utils.ensure(len(secret) == _SECRET_LENGTH, "Invalid key length")
    utils.ensure(len(discriminator) <= _DISCRIMINATOR_LENGTH, "Disc too long")

    offset = _SECRET_LENGTH
    utils.memcpy(key_buff, 0, secret, 0, _SECRET_LENGTH)

    for i in range(_SECRET_LENGTH, len(key_buff)):
        key_buff[i] = 0

    utils.memcpy(key_buff, offset, discriminator, 0, len(discriminator))
    offset += _DISCRIMINATOR_LENGTH  # fixed domain separator size

    if index is not None:
        # dump_uvarint_b_into, saving import
        shifted = True
        while shifted:
            shifted = index >> 7
            key_buff[offset] = (index & 0x7F) | (0x80 if shifted else 0x00)
            offset += 1
            index = shifted

    return crypto.keccak_2hash(key_buff, out)


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


def key_signature(master, idx: int, is_iv=False) -> bytes:
    """
    Generates signature offloading related offloading keys
    """
    return _build_key(master, b"sig-iv" if is_iv else b"sig-key", idx)


def det_comm_masks(key_enc, idx: int) -> Sc25519:
    """
    Deterministic output commitment masks
    """
    return crypto.decodeint(_build_key(key_enc, b"out-mask", idx))


def gen_hmac_vini(
    key, src_entr: MoneroTransactionSourceEntry, vini_bin: bytes, idx: int
) -> bytes:
    """
    Computes hmac (TxSourceEntry[i] || tx.vin[i])

    In src_entr.outputs only src_entr.outputs[src_entr.real_output]
    is HMACed as it is used across the protocol. Consistency of
    other values across the protocol is not required as they are
    used only once and hard to check. I.e., indices in step 2
    are uncheckable, decoy keys in step 9 are just random keys.
    """
    from trezor import protobuf
    from apps.monero.xmr.keccak_hasher import get_keccak_writer

    kwriter = get_keccak_writer()
    real_outputs = src_entr.outputs
    real_additional = src_entr.real_out_additional_tx_keys
    src_entr.outputs = [src_entr.outputs[src_entr.real_output]]
    if real_additional and len(real_additional) > 1:
        src_entr.real_out_additional_tx_keys = [
            src_entr.real_out_additional_tx_keys[src_entr.real_output_in_tx_index]
        ]

    kwriter.write(protobuf.dump_message_buffer(src_entr))
    src_entr.outputs = real_outputs
    src_entr.real_out_additional_tx_keys = real_additional
    kwriter.write(vini_bin)

    hmac_key_vini = hmac_key_txin(key, idx)
    hmac_vini = crypto.compute_hmac(hmac_key_vini, kwriter.get_digest())
    return hmac_vini


def gen_hmac_vouti(
    key, dst_entr: MoneroTransactionDestinationEntry, tx_out_bin: bytes, idx: int
) -> bytes:
    """
    Generates HMAC for (TxDestinationEntry[i] || tx.vout[i])
    """
    from trezor import protobuf
    from apps.monero.xmr.keccak_hasher import get_keccak_writer

    kwriter = get_keccak_writer()
    kwriter.write(protobuf.dump_message_buffer(dst_entr))
    kwriter.write(tx_out_bin)

    hmac_key_vouti = hmac_key_txout(key, idx)
    hmac_vouti = crypto.compute_hmac(hmac_key_vouti, kwriter.get_digest())
    return hmac_vouti


def gen_hmac_tsxdest(
    key, dst_entr: MoneroTransactionDestinationEntry, idx: int
) -> bytes:
    """
    Generates HMAC for TxDestinationEntry[i]
    """
    from trezor import protobuf
    from apps.monero.xmr.keccak_hasher import get_keccak_writer

    kwriter = get_keccak_writer()
    kwriter.write(protobuf.dump_message_buffer(dst_entr))

    hmac_key = hmac_key_txdst(key, idx)
    hmac_tsxdest = crypto.compute_hmac(hmac_key, kwriter.get_digest())
    return hmac_tsxdest


def get_ki_from_vini(vini_bin: bytes) -> bytes:
    """
    Returns key image from the TxinToKey, which is currently
    serialized as the last 32 bytes.
    """
    return bytes(vini_bin[-32:])
