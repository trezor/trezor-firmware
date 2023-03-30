"""
All outputs were set in this phase. This step serializes tx pub keys
into the tx extra field and then hashes it into the prefix hash.
The prefix hash is then complete.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import MoneroTransactionAllOutSetAck

    from apps.monero.layout import MoneroTransactionProgress

    from .state import State


def all_outputs_set(
    state: State, progress: MoneroTransactionProgress
) -> MoneroTransactionAllOutSetAck:
    import gc

    mem_trace = state.mem_trace  # local_cache_attribute

    mem_trace(0)

    progress.step(state, state.STEP_ALL_OUT)
    state.mem_trace(1)

    _validate(state)
    state.is_processing_offloaded = False
    mem_trace(2)

    extra_b = _set_tx_extra(state)
    # tx public keys not needed anymore
    state.additional_tx_public_keys = None
    state.tx_pub = None
    state.rsig_grouping = None
    state.rsig_offload = None
    gc.collect()
    mem_trace(3)

    # Completes the transaction prefix hash by including extra
    # _set_tx_prefix
    # Adds `extra` to the tx_prefix_hash, which is the last needed item,
    # so the tx_prefix_hash is now complete and can be incorporated
    # into full_message_hash.
    # Serializing "extra" type as BlobType.
    # uvarint(len(extra)) || extra
    state.tx_prefix_hasher.uvarint(len(extra_b))
    state.tx_prefix_hasher.buffer(extra_b)
    state.tx_prefix_hash = state.tx_prefix_hasher.get_digest()
    state.tx_prefix_hasher = None
    state.full_message_hasher.set_message(state.tx_prefix_hash)

    state.output_change = None
    gc.collect()
    mem_trace(4)

    # In the multisig mode here needs to be a check whether currently computed
    # transaction prefix matches expected transaction prefix sent in the
    # init step.

    from trezor.messages import MoneroRingCtSig, MoneroTransactionAllOutSetAck

    # Initializes RCTsig structure (fee, tx prefix hash, type)
    rv_pb = MoneroRingCtSig(
        txn_fee=state.fee,
        message=state.tx_prefix_hash,
        rv_type=state.tx_type,
    )

    # _out_pk
    # Hashes out_pk into the full message.
    if state.output_count != len(state.output_pk_commitments):
        raise ValueError("Invalid number of ecdh")
    for out in state.output_pk_commitments:
        state.full_message_hasher.set_out_pk_commitment(out)

    state.full_message_hasher.rctsig_base_done()
    state.current_output_index = None
    state.current_input_index = -1

    assert state.full_message_hasher is not None
    state.full_message = state.full_message_hasher.get_digest()
    state.full_message_hasher = None
    state.output_pk_commitments = None
    state.summary_outs_money = None
    state.summary_inputs_money = None
    state.fee = None
    state.last_ki = None
    state.last_step = state.STEP_ALL_OUT

    return MoneroTransactionAllOutSetAck(
        extra=extra_b,
        tx_prefix_hash=state.tx_prefix_hash,
        rv=rv_pb,
        full_message_hash=state.full_message,
    )


def _validate(state: State) -> None:
    out_money = state.summary_outs_money  # local_cache_attribute
    in_money = state.summary_inputs_money  # local_cache_attribute

    if state.last_step != state.STEP_OUT:
        raise ValueError("Invalid state transition")
    if state.current_output_index + 1 != state.output_count:
        raise ValueError("Invalid out num")

    # Fee test
    if state.fee != (in_money - out_money):
        raise ValueError(
            f"Fee invalid {state.fee} vs {in_money - out_money}, out: {out_money}"
        )

    if out_money > in_money:
        raise ValueError(
            f"Transaction inputs money ({in_money}) less than outputs money ({out_money})"
        )


def _set_tx_extra(state: State) -> bytes:
    """
    Sets tx public keys into transaction's extra.
    Extra field is supposed to be sorted (by sort_tx_extra() in the Monero)
    Tag ordering: TX_EXTRA_TAG_PUBKEY, TX_EXTRA_TAG_ADDITIONAL_PUBKEYS, TX_EXTRA_NONCE
    """
    from trezor import utils

    from apps.monero.xmr import crypto
    from apps.monero.xmr.serialize import int_serialize

    extra_nonce = state.extra_nonce  # local_cache_attribute

    # Extra buffer length computation
    # TX_EXTRA_TAG_PUBKEY (1B) | tx_pub_key (32B)
    extra_size = 33
    offset = 0
    num_keys = 0
    len_size = 0

    if state.need_additional_txkeys:
        num_keys = len(state.additional_tx_public_keys)
        len_size = int_serialize.uvarint_size(num_keys)

        # TX_EXTRA_TAG_ADDITIONAL_PUBKEYS (1B) | varint | keys
        extra_size += 1 + len_size + 32 * num_keys

    if extra_nonce:
        extra_size += len(extra_nonce)

    extra = bytearray(extra_size)
    extra[0] = 1  # TX_EXTRA_TAG_PUBKEY
    crypto.encodepoint_into(memoryview(extra)[1:], state.tx_pub)
    offset += 33

    if state.need_additional_txkeys:
        extra[offset] = 0x4  # TX_EXTRA_TAG_ADDITIONAL_PUBKEYS
        int_serialize.dump_uvarint_b_into(num_keys, extra, offset + 1)
        offset += 1 + len_size

        for idx in range(num_keys):
            extra[offset : offset + 32] = state.additional_tx_public_keys[idx]
            offset += 32

    if extra_nonce:
        utils.memcpy(extra, offset, extra_nonce, 0, len(extra_nonce))
        state.extra_nonce = None

    return extra
