"""
All outputs were set in this phase. This step serializes tx pub keys
into the tx extra field and then hashes it into the prefix hash.
The prefix hash is then complete.
"""

import gc

from trezor import utils

from .state import State

from apps.monero.layout import confirms
from apps.monero.signing import get_monero_rct_type
from apps.monero.xmr import crypto


async def all_outputs_set(state: State):
    state.mem_trace(0)

    await confirms.transaction_step(state.ctx, state.STEP_ALL_OUT)
    state.mem_trace(1)

    _validate(state)
    state.mem_trace(2)

    _set_tx_extra(state)
    # tx public keys not needed anymore
    state.additional_tx_public_keys = None
    state.tx_pub = None
    gc.collect()
    state.mem_trace(3)

    # Completes the transaction prefix hash by including extra
    _set_tx_prefix(state)
    extra_b = state.tx.extra
    state.tx = None
    gc.collect()
    state.mem_trace(4)

    # In the multisig mode here needs to be a check whether currently computed
    # transaction prefix matches expected transaction prefix sent in the
    # init step.

    from trezor.messages.MoneroRingCtSig import MoneroRingCtSig
    from trezor.messages.MoneroTransactionAllOutSetAck import (
        MoneroTransactionAllOutSetAck,
    )

    # Initializes RCTsig structure (fee, tx prefix hash, type)
    rv_pb = MoneroRingCtSig(
        txn_fee=state.fee,
        message=state.tx_prefix_hash,
        rv_type=get_monero_rct_type(state.rct_type, state.rsig_type),
    )

    _out_pk(state)
    state.full_message_hasher.rctsig_base_done()
    state.current_output_index = -1
    state.current_input_index = -1

    state.full_message = state.full_message_hasher.get_digest()
    state.full_message_hasher = None

    return MoneroTransactionAllOutSetAck(
        extra=extra_b,
        tx_prefix_hash=state.tx_prefix_hash,
        rv=rv_pb,
        full_message_hash=state.full_message,
    )


def _validate(state: State):
    from apps.monero.signing import RctType

    if state.current_output_index + 1 != state.output_count:
        raise ValueError("Invalid out num")

    # Test if \sum Alpha == \sum A
    if state.rct_type == RctType.Simple:
        utils.ensure(crypto.sc_eq(state.sumout, state.sumpouts_alphas))

    # Fee test
    if state.fee != (state.summary_inputs_money - state.summary_outs_money):
        raise ValueError(
            "Fee invalid %s vs %s, out: %s"
            % (
                state.fee,
                state.summary_inputs_money - state.summary_outs_money,
                state.summary_outs_money,
            )
        )

    if state.summary_outs_money > state.summary_inputs_money:
        raise ValueError(
            "Transaction inputs money (%s) less than outputs money (%s)"
            % (state.summary_inputs_money, state.summary_outs_money)
        )


def _set_tx_extra(state: State):
    """
    Sets tx public keys into transaction's extra.
    """
    state.tx.extra = _add_tx_pub_key_to_extra(state.tx.extra, state.tx_pub)

    if state.need_additional_txkeys:
        state.tx.extra = _add_additional_tx_pub_keys_to_extra(
            state.tx.extra, state.additional_tx_public_keys
        )


def _set_tx_prefix(state: State):
    """
    Adds `extra` to the tx_prefix_hash, which is the last needed item,
    so the tx_prefix_hash is now complete and can be incorporated
    into full_message_hash.
    """
    # Serializing "extra" type as BlobType.
    # uvarint(len(extra)) || extra
    state.tx_prefix_hasher.uvarint(len(state.tx.extra))
    state.tx_prefix_hasher.buffer(state.tx.extra)

    state.tx_prefix_hash = state.tx_prefix_hasher.get_digest()
    state.tx_prefix_hasher = None

    state.full_message_hasher.set_message(state.tx_prefix_hash)


def _add_tx_pub_key_to_extra(tx_extra, pub_key):
    """
    Adds public key to the extra
    """
    to_add = bytearray(33)
    to_add[0] = 1  # TX_EXTRA_TAG_PUBKEY
    crypto.encodepoint_into(memoryview(to_add)[1:], pub_key)
    return tx_extra + to_add


def _add_additional_tx_pub_keys_to_extra(tx_extra, pub_keys):
    """
    Adds all additional tx public keys to the extra buffer
    """
    from apps.monero.xmr.serialize import int_serialize

    # format: variant_tag (0x4) | array len varint | 32B | 32B | ...
    num_keys = len(pub_keys)
    len_size = int_serialize.uvarint_size(num_keys)
    buffer = bytearray(1 + len_size + 32 * num_keys)

    buffer[0] = 0x4  # TX_EXTRA_TAG_ADDITIONAL_PUBKEYS
    int_serialize.dump_uvarint_b_into(num_keys, buffer, 1)  # uvarint(num_keys)
    offset = 1 + len_size

    for idx in range(num_keys):
        buffer[offset : offset + 32] = pub_keys[idx]
        offset += 32

    tx_extra += buffer
    return tx_extra


def _out_pk(state: State):
    """
    Hashes out_pk into the full message.
    """
    if state.output_count != len(state.output_pk_commitments):
        raise ValueError("Invalid number of ecdh")

    for out in state.output_pk_commitments:
        state.full_message_hasher.set_out_pk_commitment(out)
