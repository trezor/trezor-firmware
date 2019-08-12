from micropython import const
from trezor import wire, loop
from trezor.crypto.hashlib import blake2b
from trezor.utils import HashWriter
from trezor.crypto.curve import ed25519
from trezor.messages.TezosSignedBakerOp import TezosSignedBakerOp
from trezor.messages.Failure import Failure
from apps.common.storage import common

from apps.tezos import CURVE, helpers, layout
from apps.common.writers import (
    write_bytes,
    write_uint8,
    write_uint16_be,
    write_uint32_be,
    write_uint64_be,
)

BLOCK_WATERMARK = const(1)
ENDORSEMENT_WATERMARK = const(2)
ENDORSEMENT_TAG = const(0)


async def sign_baker_op(ctx, msg, keychain):
    # paths.validate_path(ctx, helpers.validate_full_path, path=msg.address_n)

    if not helpers.validate_full_path(msg.address_n):
        return Failure()

    # the level should be greater than the last signed, with this check we avoid double baking/endorsement
    if msg.endorsement and helpers.get_last_endorsement_level() >= msg.endorsement.level:
        raise wire.DataError("Potential double endorsement")

    if msg.block_header and helpers.get_last_block_level() >= msg.block_header.level:
        raise wire.DataError("Potential double baking")

    node = keychain.derive(msg.address_n, CURVE)

    sig_prefixed = await _sign(ctx, node, msg)

    return TezosSignedBakerOp(signature=sig_prefixed)


def _write_operation_bytes(w: bytearray, msg):

    if msg.endorsement is not None:
        write_uint8(w, ENDORSEMENT_WATERMARK)
        write_bytes(w, msg.chain_id)
        write_bytes(w, msg.endorsement.branch)
        write_uint8(w, ENDORSEMENT_TAG)
        write_uint32_be(w, msg.endorsement.level)

    elif msg.block_header is not None:
        write_uint8(w, BLOCK_WATERMARK)
        write_bytes(w, msg.chain_id)
        write_uint32_be(w, msg.block_header.level)
        write_uint8(w, msg.block_header.proto)
        write_bytes(w, msg.block_header.predecessor)
        write_uint64_be(w, msg.block_header.timestamp)
        write_uint8(w, msg.block_header.validation_pass)
        write_bytes(w, msg.block_header.operations_hash)
        write_uint32_be(w, msg.block_header.bytes_in_field_fitness)
        write_uint32_be(w, msg.block_header.bytes_in_next_field)
        write_bytes(w, msg.block_header.fitness)
        write_bytes(w, msg.block_header.context)
        write_uint16_be(w, msg.block_header.priority)
        write_bytes(w, msg.block_header.proof_of_work_nonce)
        helpers.write_bool(w, msg.block_header.presence_of_field_seed_nonce_hash)
        if msg.block_header.seed_nonce_hash:
            write_bytes(w, msg.block_header.seed_nonce_hash)


async def _sign(ctx, node, msg):
    h_sign = HashWriter(blake2b(outlen=32))

    _write_operation_bytes(h_sign, msg)
    wm_opbytes_hash = h_sign.get_digest()

    signature = ed25519.sign(node.private_key(), wm_opbytes_hash)
    sig_prefixed = helpers.base58_encode_check(
        signature, prefix=helpers.TEZOS_SIGNATURE_PREFIX
    )

    if msg.endorsement is not None:
        helpers.set_last_endorsement_level(msg.endorsement.level)
        helpers.set_last_type(ENDORSEMENT_WATERMARK)
    elif msg.block_header is not None:
        helpers.set_last_block_level(msg.block_header.level)
        helpers.set_last_type(BLOCK_WATERMARK)
    return sig_prefixed
