"""
Output destinations are streamed one by one.
Computes destination one-time address, amount key, range proof + HMAC, out_pk, ecdh_info.
"""
import gc

from trezor import utils

from apps.monero import signing
from apps.monero.layout import confirms
from apps.monero.signing import offloading_keys
from apps.monero.xmr import crypto, serialize

from .state import State

if False:
    from apps.monero.xmr.types import Sc25519, Ge25519
    from apps.monero.xmr.serialize_messages.tx_ecdh import EcdhTuple
    from apps.monero.xmr.serialize_messages.tx_rsig_bulletproof import Bulletproof
    from trezor.messages import (
        MoneroTransactionDestinationEntry,
        MoneroTransactionSetOutputAck,
        MoneroTransactionRsigData,
    )


async def set_output(
    state: State,
    dst_entr: MoneroTransactionDestinationEntry,
    dst_entr_hmac: bytes,
    rsig_data: MoneroTransactionRsigData,
    is_offloaded_bp=False,
) -> MoneroTransactionSetOutputAck:
    state.mem_trace(0, True)
    mods = utils.unimport_begin()

    # Progress update only for master message (skip for offloaded BP msg)
    if not is_offloaded_bp:
        await confirms.transaction_step(
            state, state.STEP_OUT, state.current_output_index + 1
        )

    state.mem_trace(1, True)

    dst_entr = _validate(state, dst_entr, dst_entr_hmac, is_offloaded_bp)
    state.mem_trace(2, True)

    if not state.is_processing_offloaded:
        # First output - we include the size of the container into the tx prefix hasher
        if state.current_output_index == 0:
            state.tx_prefix_hasher.uvarint(state.output_count)

        state.mem_trace(4, True)
        state.output_amounts.append(dst_entr.amount)
        state.summary_outs_money += dst_entr.amount

    utils.unimport_end(mods)
    state.mem_trace(5, True)

    # Compute tx keys and masks if applicable
    tx_out_key, amount_key = _compute_tx_keys(state, dst_entr)
    utils.unimport_end(mods)
    state.mem_trace(6, True)

    # Range proof first, memory intensive (fragmentation)
    rsig_data_new, mask = _range_proof(state, rsig_data)
    utils.unimport_end(mods)
    state.mem_trace(7, True)

    # If det masks & offloading, return as we are handling offloaded BP.
    if state.is_processing_offloaded:
        from trezor.messages import MoneroTransactionSetOutputAck

        return MoneroTransactionSetOutputAck()

    # Tx header prefix hashing, hmac dst_entr
    tx_out_bin, hmac_vouti = _set_out_tx_out(state, dst_entr, tx_out_key)
    state.mem_trace(11, True)

    out_pk_dest, out_pk_commitment, ecdh_info_bin = _get_ecdh_info_and_out_pk(
        state=state,
        tx_out_key=tx_out_key,
        amount=dst_entr.amount,
        mask=mask,
        amount_key=amount_key,
    )
    del (dst_entr, mask, amount_key, tx_out_key)
    state.mem_trace(12, True)

    # Incremental hashing of the ECDH info.
    # RctSigBase allows to hash only one of the (ecdh, out_pk) as they are serialized
    # as whole vectors. We choose to hash ECDH first, because it saves state space.
    state.full_message_hasher.set_ecdh(ecdh_info_bin)
    state.mem_trace(13, True)

    # output_pk_commitment is stored to the state as it is used during the signature and hashed to the
    # RctSigBase later. No need to store amount, it was already stored.
    state.output_pk_commitments.append(out_pk_commitment)
    state.last_step = state.STEP_OUT
    state.mem_trace(14, True)

    from trezor.messages import MoneroTransactionSetOutputAck

    out_pk_bin = bytearray(64)
    utils.memcpy(out_pk_bin, 0, out_pk_dest, 0, 32)
    utils.memcpy(out_pk_bin, 32, out_pk_commitment, 0, 32)

    return MoneroTransactionSetOutputAck(
        tx_out=tx_out_bin,
        vouti_hmac=hmac_vouti,
        rsig_data=rsig_data_new,
        out_pk=out_pk_bin,
        ecdh_info=ecdh_info_bin,
    )


def _validate(
    state: State,
    dst_entr: MoneroTransactionDestinationEntry,
    dst_entr_hmac: bytes,
    is_offloaded_bp: bool,
) -> MoneroTransactionDestinationEntry:
    if state.last_step not in (state.STEP_ALL_IN, state.STEP_OUT):
        raise ValueError("Invalid state transition")
    if is_offloaded_bp and (not state.rsig_offload):
        raise ValueError("Extraneous offloaded msg")

    if state.rsig_offload:
        bidx = _get_rsig_batch(state, state.current_output_index)
        last_in_batch = _is_last_in_batch(state, state.current_output_index, bidx)

        utils.ensure(
            not last_in_batch or state.is_processing_offloaded != is_offloaded_bp,
            "Offloaded BP out of order",
        )
        state.is_processing_offloaded = is_offloaded_bp

    if not state.is_processing_offloaded:
        state.current_output_index += 1

    utils.ensure(
        not dst_entr or dst_entr.amount >= 0, "Destination with negative amount"
    )
    utils.ensure(
        state.current_input_index + 1 == state.input_count, "Invalid number of inputs"
    )
    utils.ensure(
        state.current_output_index < state.output_count, "Invalid output index"
    )

    if not state.is_processing_offloaded:
        # HMAC check of the destination
        dst_entr_hmac_computed = offloading_keys.gen_hmac_tsxdest(
            state.key_hmac, dst_entr, state.current_output_index
        )

        utils.ensure(
            crypto.ct_equals(dst_entr_hmac, dst_entr_hmac_computed), "HMAC failed"
        )
        del dst_entr_hmac_computed

    else:
        dst_entr = None

    del dst_entr_hmac
    state.mem_trace(3, True)

    return dst_entr


def _compute_tx_keys(
    state: State, dst_entr: MoneroTransactionDestinationEntry
) -> tuple[Ge25519, Sc25519]:
    """Computes tx_out_key, amount_key"""

    if state.is_processing_offloaded:
        return None, None  # no need to recompute

    # additional tx key if applicable
    additional_txkey_priv = _set_out_additional_keys(state, dst_entr)
    # derivation = a*R or r*A or s*C
    derivation = _set_out_derivation(state, dst_entr, additional_txkey_priv)
    # amount key = H_s(derivation || i)
    amount_key = crypto.derivation_to_scalar(derivation, state.current_output_index)
    # one-time destination address P = H_s(derivation || i)*G + B
    tx_out_key = crypto.derive_public_key(
        derivation,
        state.current_output_index,
        crypto.decodepoint(dst_entr.addr.spend_public_key),
    )
    del (derivation, additional_txkey_priv)

    from apps.monero.xmr import monero

    mask = monero.commitment_mask(crypto.encodeint(amount_key))
    state.output_masks.append(mask)
    return tx_out_key, amount_key


def _set_out_tx_out(
    state: State, dst_entr: MoneroTransactionDestinationEntry, tx_out_key: Ge25519
) -> tuple[bytes, bytes]:
    """
    Manually serializes TxOut(0, TxoutToKey(key)) and calculates hmac.
    """
    tx_out_bin = bytearray(34)
    tx_out_bin[0] = 0  # amount varint
    tx_out_bin[1] = 2  # variant code TxoutToKey
    crypto.encodepoint_into(tx_out_bin, tx_out_key, 2)
    state.mem_trace(8)

    # Tx header prefix hashing
    state.tx_prefix_hasher.buffer(tx_out_bin)
    state.mem_trace(9, True)

    # Hmac dst_entr
    hmac_vouti = offloading_keys.gen_hmac_vouti(
        state.key_hmac, dst_entr, tx_out_bin, state.current_output_index
    )
    state.mem_trace(10, True)
    return tx_out_bin, hmac_vouti


def _range_proof(
    state: State, rsig_data: MoneroTransactionRsigData
) -> tuple[MoneroTransactionRsigData, Sc25519]:
    """
    Computes rangeproof and handles range proof offloading logic.

    Since HF10 the commitments are deterministic.
    The range proof is incrementally hashed to the final_message.
    """
    provided_rsig = None
    if rsig_data and rsig_data.rsig and len(rsig_data.rsig) > 0:
        provided_rsig = rsig_data.rsig
    if not state.rsig_offload and provided_rsig:
        raise signing.Error("Provided unexpected rsig")

    # Batching & validation
    bidx = _get_rsig_batch(state, state.current_output_index)
    last_in_batch = _is_last_in_batch(state, state.current_output_index, bidx)
    if state.rsig_offload and provided_rsig and not last_in_batch:
        raise signing.Error("Provided rsig too early")

    if (
        state.rsig_offload
        and last_in_batch
        and not provided_rsig
        and state.is_processing_offloaded
    ):
        raise signing.Error("Rsig expected, not provided")

    # Batch not finished, skip range sig generation now
    mask = state.output_masks[-1] if not state.is_processing_offloaded else None
    offload_mask = mask and state.rsig_offload

    # If not last, do not proceed to the BP processing.
    if not last_in_batch:
        rsig_data_new = (
            _return_rsig_data(mask=crypto.encodeint(mask)) if offload_mask else None
        )
        return rsig_data_new, mask

    # Rangeproof
    # Pedersen commitment on the value, mask from the commitment, range signature.
    rsig = None

    state.mem_trace("pre-rproof" if __debug__ else None, collect=True)
    if not state.rsig_offload:
        """Bulletproof calculation in Trezor"""
        rsig = _rsig_bp(state)

    elif not state.is_processing_offloaded:
        """Bulletproof offloaded to the host, deterministic masks. Nothing here, waiting for offloaded BP."""
        pass

    else:
        """Bulletproof offloaded to the host, check BP, hash it."""
        _rsig_process_bp(state, rsig_data)

    state.mem_trace("rproof" if __debug__ else None, collect=True)

    # Construct new rsig data to send back to the host.
    rsig_data_new = _return_rsig_data(
        rsig, crypto.encodeint(mask) if offload_mask else None
    )

    if state.current_output_index + 1 == state.output_count and (
        not state.rsig_offload or state.is_processing_offloaded
    ):
        # output masks and amounts are not needed anymore
        state.output_amounts = None
        state.output_masks = None

    return rsig_data_new, mask


def _rsig_bp(state: State) -> bytes:
    """Bulletproof calculation in trezor"""
    from apps.monero.xmr import range_signatures

    rsig = range_signatures.prove_range_bp_batch(
        state.output_amounts, state.output_masks
    )
    state.mem_trace("post-bp" if __debug__ else None, collect=True)

    # Incremental BP hashing
    # BP is hashed with raw=False as hash does not contain L, R
    # array sizes compared to the serialized bulletproof format
    # thus direct serialization cannot be used.
    state.full_message_hasher.rsig_val(rsig, raw=False)
    state.mem_trace("post-bp-hash" if __debug__ else None, collect=True)

    rsig = _dump_rsig_bp(rsig)
    state.mem_trace(
        "post-bp-ser, size: %s" % len(rsig) if __debug__ else None, collect=True
    )

    # state cleanup
    state.output_masks = []
    state.output_amounts = []
    return rsig


def _rsig_process_bp(state: State, rsig_data: MoneroTransactionRsigData):
    from apps.monero.xmr import range_signatures
    from apps.monero.xmr.serialize_messages.tx_rsig_bulletproof import Bulletproof

    bp_obj = serialize.parse_msg(rsig_data.rsig, Bulletproof)
    rsig_data.rsig = None

    # BP is hashed with raw=False as hash does not contain L, R
    # array sizes compared to the serialized bulletproof format
    # thus direct serialization cannot be used.
    state.full_message_hasher.rsig_val(bp_obj, raw=False)
    res = range_signatures.verify_bp(bp_obj, state.output_amounts, state.output_masks)
    utils.ensure(res, "BP verification fail")
    state.mem_trace("BP verified" if __debug__ else None, collect=True)
    del (bp_obj, range_signatures)

    # State cleanup after verification is finished
    state.output_amounts = []
    state.output_masks = []


def _dump_rsig_bp(rsig: Bulletproof) -> bytes:
    if len(rsig.L) > 127:
        raise ValueError("Too large")

    # Manual serialization as the generic purpose serialize.dump_msg_gc
    # is more memory intensive which is not desired in the range proof section.

    # BP: V, A, S, T1, T2, taux, mu, L, R, a, b, t
    # Commitment vector V is not serialized
    # Vector size under 127 thus varint occupies 1 B
    buff_size = 32 * (9 + 2 * (len(rsig.L))) + 2
    buff = bytearray(buff_size)

    utils.memcpy(buff, 0, rsig.A, 0, 32)
    utils.memcpy(buff, 32, rsig.S, 0, 32)
    utils.memcpy(buff, 32 * 2, rsig.T1, 0, 32)
    utils.memcpy(buff, 32 * 3, rsig.T2, 0, 32)
    utils.memcpy(buff, 32 * 4, rsig.taux, 0, 32)
    utils.memcpy(buff, 32 * 5, rsig.mu, 0, 32)

    buff[32 * 6] = len(rsig.L)
    offset = 32 * 6 + 1

    for x in rsig.L:
        utils.memcpy(buff, offset, x, 0, 32)
        offset += 32

    buff[offset] = len(rsig.R)
    offset += 1

    for x in rsig.R:
        utils.memcpy(buff, offset, x, 0, 32)
        offset += 32

    utils.memcpy(buff, offset, rsig.a, 0, 32)
    offset += 32
    utils.memcpy(buff, offset, rsig.b, 0, 32)
    offset += 32
    utils.memcpy(buff, offset, rsig.t, 0, 32)
    return buff


def _return_rsig_data(
    rsig: bytes = None, mask: bytes = None
) -> MoneroTransactionRsigData:
    if rsig is None and mask is None:
        return None

    from trezor.messages import MoneroTransactionRsigData

    rsig_data = MoneroTransactionRsigData()

    if mask:
        rsig_data.mask = mask

    if rsig:
        rsig_data.rsig = rsig

    return rsig_data


def _get_ecdh_info_and_out_pk(
    state: State, tx_out_key: Ge25519, amount: int, mask: Sc25519, amount_key: Sc25519
) -> tuple[bytes, bytes, bytes]:
    """
    Calculates the Pedersen commitment C = aG + bH and returns it as CtKey.
    Also encodes the two items - `mask` and `amount` - into ecdh info,
    so the recipient is able to reconstruct the commitment.
    """
    out_pk_dest = crypto.encodepoint(tx_out_key)
    out_pk_commitment = crypto.encodepoint(crypto.gen_commitment(mask, amount))
    crypto.sc_add_into(state.sumout, state.sumout, mask)
    ecdh_info = _ecdh_encode(amount, crypto.encodeint(amount_key))

    # Manual ECDH info serialization
    ecdh_info_bin = _serialize_ecdh(ecdh_info)
    gc.collect()

    return out_pk_dest, out_pk_commitment, ecdh_info_bin


def _serialize_ecdh(ecdh_info: EcdhTuple) -> bytes:
    """
    Serializes ECDH according to the current format defined by the hard fork version
    or the signature format respectively.
    """
    # Since HF10 the amount is serialized to 8B and mask is deterministic
    ecdh_info_bin = bytearray(8)
    ecdh_info_bin[:] = ecdh_info.amount[0:8]
    return ecdh_info_bin


def _ecdh_hash(shared_sec: bytes) -> bytes:
    """
    Generates ECDH hash for amount masking for Bulletproof2
    """
    data = bytearray(38)
    data[0:6] = b"amount"
    data[6:] = shared_sec
    return crypto.cn_fast_hash(data)


def _ecdh_encode(amount: int, amount_key: bytes) -> EcdhTuple:
    """
    Output recipients decode amounts from EcdhTuple structure.
    """
    from apps.monero.xmr.serialize_messages.tx_ecdh import EcdhTuple

    ecdh_info = EcdhTuple(mask=crypto.NULL_KEY_ENC, amount=bytearray(32))
    amnt = crypto.sc_init(amount)
    crypto.encodeint_into(ecdh_info.amount, amnt)
    crypto.xor8(ecdh_info.amount, _ecdh_hash(amount_key))
    return ecdh_info


def _set_out_additional_keys(
    state: State, dst_entr: MoneroTransactionDestinationEntry
) -> Sc25519:
    """
    If needed (decided in step 1), additional tx keys are calculated
    for this particular output.
    """
    if not state.need_additional_txkeys:
        return None

    additional_txkey_priv = crypto.random_scalar()

    if dst_entr.is_subaddress:
        # R=r*D
        additional_txkey = crypto.decodepoint(dst_entr.addr.spend_public_key)
        crypto.scalarmult_into(
            additional_txkey, additional_txkey, additional_txkey_priv
        )
    else:
        # R=r*G
        additional_txkey = crypto.scalarmult_base(additional_txkey_priv)

    state.additional_tx_public_keys.append(crypto.encodepoint(additional_txkey))
    state.additional_tx_private_keys.append(additional_txkey_priv)
    return additional_txkey_priv


def _set_out_derivation(
    state: State,
    dst_entr: MoneroTransactionDestinationEntry,
    additional_txkey_priv: Sc25519,
) -> Ge25519:
    """
    Calculates derivation which is then used in the one-time address as
    `P = H(derivation)*G + B`.
    For change outputs the derivation equals a*R, because we know the
    private view key. For others it is either `r*A` for traditional
    addresses, or `s*C` for subaddresses. Both `r` and `s` are random
    scalars, `s` is used in the context of subaddresses, but it's
    basically the same thing.
    """
    from apps.monero.xmr.addresses import addr_eq

    change_addr = state.change_address()
    if change_addr and addr_eq(dst_entr.addr, change_addr):
        # sending change to yourself; derivation = a*R
        derivation = crypto.generate_key_derivation(
            state.tx_pub, state.creds.view_key_private
        )

    else:
        # sending to the recipient; derivation = r*A (or s*C in the subaddress scheme)
        if dst_entr.is_subaddress and state.need_additional_txkeys:
            deriv_priv = additional_txkey_priv
        else:
            deriv_priv = state.tx_priv
        derivation = crypto.generate_key_derivation(
            crypto.decodepoint(dst_entr.addr.view_public_key), deriv_priv
        )
    return derivation


def _is_last_in_batch(state: State, idx: int, bidx: int) -> bool:
    """
    Returns true if the current output is last in the rsig batch
    """
    batch_size = state.rsig_grouping[bidx]
    return (idx - sum(state.rsig_grouping[:bidx])) + 1 == batch_size


def _get_rsig_batch(state: State, idx: int) -> int:
    """
    Returns index of the current rsig batch
    """
    r = 0
    c = 0
    while c < idx + 1:
        c += state.rsig_grouping[r]
        r += 1
    return r - 1
