from ubinascii import hexlify

from trezor.crypto.curve import ed25519
from trezor.crypto.hashlib import sha256
from trezor.messages import StellarSignedTx, StellarSignTx, StellarTxOpRequest
from trezor.wire import ProcessError

from apps.common import paths, seed
from apps.common.keychain import auto_keychain

from . import consts, helpers, layout, writers
from .operations import process_operation


@auto_keychain(__name__)
async def sign_tx(ctx, msg: StellarSignTx, keychain):
    await paths.validate_path(ctx, keychain, msg.address_n)

    node = keychain.derive(msg.address_n)
    pubkey = seed.remove_ed25519_prefix(node.public_key())

    if msg.num_operations == 0:
        raise ProcessError("Stellar: At least one operation is required")

    w = bytearray()
    await _init(ctx, w, pubkey, msg)
    await _timebounds(ctx, w, msg.timebounds_start, msg.timebounds_end)
    await _memo(ctx, w, msg)
    await _operations(ctx, w, msg.num_operations)
    await _final(ctx, w, msg)

    # sign
    digest = sha256(w).digest()
    signature = ed25519.sign(node.private_key(), digest)

    # Add the public key for verification that the right account was used for signing
    return StellarSignedTx(public_key=pubkey, signature=signature)


async def _final(ctx, w: bytearray, msg: StellarSignTx):
    # 4 null bytes representing a (currently unused) empty union
    writers.write_uint32(w, 0)
    # final confirm
    await layout.require_confirm_final(ctx, msg.fee, msg.num_operations)


async def _init(ctx, w: bytearray, pubkey: bytes, msg: StellarSignTx):
    network_passphrase_hash = sha256(msg.network_passphrase).digest()
    writers.write_bytes_fixed(w, network_passphrase_hash, 32)
    writers.write_bytes_fixed(w, consts.TX_TYPE, 4)

    address = helpers.address_from_public_key(pubkey)
    accounts_match = msg.source_account == address

    writers.write_pubkey(w, msg.source_account)
    writers.write_uint32(w, msg.fee)
    writers.write_uint64(w, msg.sequence_number)

    # confirm init
    await layout.require_confirm_init(
        ctx, msg.source_account, msg.network_passphrase, accounts_match
    )


async def _timebounds(ctx, w: bytearray, start: int, end: int):
    # timebounds are only present if timebounds_start or timebounds_end is non-zero
    if start or end:
        # confirm dialog
        await layout.require_confirm_timebounds(ctx, start, end)
        writers.write_bool(w, True)

        # timebounds are sent as uint32s since that's all we can display, but they must be hashed as 64bit
        writers.write_uint64(w, start or 0)
        writers.write_uint64(w, end or 0)
    else:
        writers.write_bool(w, False)


async def _operations(ctx, w: bytearray, num_operations: int):
    writers.write_uint32(w, num_operations)
    for i in range(num_operations):
        op = await ctx.call_any(StellarTxOpRequest(), *consts.op_wire_types)
        await process_operation(ctx, w, op)


async def _memo(ctx, w: bytearray, msg: StellarSignTx):
    if msg.memo_type is None:
        msg.memo_type = consts.MEMO_TYPE_NONE
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
        writers.write_bytes_fixed(w, bytearray(msg.memo_hash), 32)
        memo_confirm_text = hexlify(msg.memo_hash).decode()
    else:
        raise ProcessError("Stellar invalid memo type")
    await layout.require_confirm_memo(ctx, msg.memo_type, memo_confirm_text)
