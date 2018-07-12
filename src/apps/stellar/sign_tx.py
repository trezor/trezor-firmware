from ubinascii import hexlify

from trezor.crypto.curve import ed25519
from trezor.crypto.hashlib import sha256
from trezor.messages.StellarSignedTx import StellarSignedTx
from trezor.messages.StellarSignTx import StellarSignTx
from trezor.messages.StellarTxOpRequest import StellarTxOpRequest
from trezor.wire import ProcessError

from apps.common import seed
from apps.stellar import consts, helpers, layout, writers
from apps.stellar.operations import operation


async def sign_tx(ctx, msg: StellarSignTx):
    if msg.num_operations == 0:
        raise ProcessError("Stellar: At least one operation is required")

    node = await seed.derive_node(ctx, msg.address_n, consts.STELLAR_CURVE)
    pubkey = seed.remove_ed25519_prefix(node.public_key())

    w = bytearray()
    await _init(ctx, w, pubkey, msg)
    _timebounds(w, msg.timebounds_start, msg.timebounds_end)
    await _memo(ctx, w, msg)
    await _operations(ctx, w, msg.num_operations)
    await _final(ctx, w, msg)

    # sign
    digest = sha256(w).digest()
    signature = ed25519.sign(node.private_key(), digest)

    # Add the public key for verification that the right account was used for signing
    return StellarSignedTx(pubkey, signature)


async def _final(ctx, w: bytearray, msg: StellarSignTx):
    # 4 null bytes representing a (currently unused) empty union
    writers.write_uint32(w, 0)
    # final confirm
    await layout.require_confirm_final(ctx, msg.fee, msg.num_operations)


async def _init(ctx, w: bytearray, pubkey: bytes, msg: StellarSignTx):
    network_passphrase_hash = sha256(msg.network_passphrase).digest()
    writers.write_bytes(w, network_passphrase_hash)
    writers.write_bytes(w, consts.TX_TYPE)

    address = helpers.address_from_public_key(pubkey)
    writers.write_pubkey(w, address)
    if helpers.public_key_from_address(msg.source_account) != pubkey:
        raise ProcessError("Stellar: source account does not match address_n")
    writers.write_uint32(w, msg.fee)
    writers.write_uint64(w, msg.sequence_number)

    # confirm init
    await layout.require_confirm_init(ctx, address, msg.network_passphrase)


def _timebounds(w: bytearray, start: int, end: int):
    # timebounds are only present if timebounds_start or timebounds_end is non-zero
    if start or end:
        writers.write_bool(w, True)
        # timebounds are sent as uint32s since that's all we can display, but they must be hashed as 64bit
        writers.write_uint64(w, start)
        writers.write_uint64(w, end)
    else:
        writers.write_bool(w, False)


async def _operations(ctx, w: bytearray, num_operations: int):
    writers.write_uint32(w, num_operations)
    for i in range(num_operations):
        op = await ctx.call(StellarTxOpRequest(), *consts.op_wire_types)
        await operation(ctx, w, op)


async def _memo(ctx, w: bytearray, msg: StellarSignTx):
    writers.write_uint32(w, msg.memo_type)
    if msg.memo_type == consts.MEMO_TYPE_NONE:
        # nothing is serialized
        memo_confirm_text = ""
    elif msg.memo_type == consts.MEMO_TYPE_TEXT:
        # Text: 4 bytes (size) + up to 28 bytes
        if len(msg.memo_text) > 28:
            raise ProcessError("Stellar: max length of a memo text is 28 bytes")
        writers.write_string(w, msg.memo_text)
        memo_confirm_text = msg.memo_text
    elif msg.memo_type == consts.MEMO_TYPE_ID:
        # ID: 64 bit unsigned integer
        writers.write_uint64(w, msg.memo_id)
        memo_confirm_text = str(msg.memo_id)
    elif msg.memo_type in (consts.MEMO_TYPE_HASH, consts.MEMO_TYPE_RETURN):
        # Hash/Return: 32 byte hash
        writers.write_bytes(w, bytearray(msg.memo_hash))
        memo_confirm_text = hexlify(msg.memo_hash).decode()
    else:
        raise ProcessError("Stellar invalid memo type")
    await layout.require_confirm_memo(ctx, msg.memo_type, memo_confirm_text)
