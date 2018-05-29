from apps.common import seed
from apps.stellar.writers import *
from apps.stellar.operations import serialize_op
from apps.stellar.consts import op_wire_types
from apps.stellar.layout import require_confirm_init, require_confirm_final
from apps.stellar import helpers
from trezor.messages.StellarSignTx import StellarSignTx
from trezor.messages.StellarTxOpRequest import StellarTxOpRequest
from trezor.messages.StellarSignedTx import StellarSignedTx
from trezor.crypto.curve import ed25519
from trezor.crypto.hashlib import sha256

STELLAR_CURVE = 'ed25519'
TX_TYPE = bytearray('\x00\x00\x00\x02')


async def sign_tx_loop(ctx, msg: StellarSignTx):
    signer = sign_tx(msg, msg)
    res = None
    while True:
        req = signer.send(res)
        if isinstance(req, StellarTxOpRequest):
            res = await ctx.call(req, *op_wire_types)
        elif isinstance(req, StellarSignedTx):
            break
        elif isinstance(req, helpers.UiConfirmInit):
            res = await require_confirm_init(ctx, req.pubkey, req.network)
        elif isinstance(req, helpers.UiConfirmFinal):
            res = await require_confirm_final(ctx, req.fee, req.num_operations)
        else:
            raise TypeError('Stellar: Invalid signing instruction')
    return req


async def sign_tx(ctx, msg):
    if msg.num_operations == 0:
        raise ValueError('Stellar: At least one operation is required')

    network_passphrase_hash = sha256(msg.network_passphrase).digest()

    # Stellar transactions consist of sha256 of:
    # - sha256(network passphrase)
    # - 4-byte unsigned big-endian int type constant (2 for tx)
    # - public key

    w = bytearray()
    write_bytes(w, network_passphrase_hash)
    write_bytes(w, TX_TYPE)

    node = await seed.derive_node(ctx, msg.address_n, STELLAR_CURVE)
    pubkey = seed.remove_ed25519_public_key_prefix(node.public_key())
    write_pubkey(w, pubkey)
    if msg.source_account != pubkey:
        raise ValueError('Stellar: source account does not match address_n')

    write_uint32(w, msg.fee)
    write_uint64(w, msg.sequence_number)

    # timebounds are only present if timebounds_start or timebounds_end is non-zero
    if msg.timebounds_start or msg.timebounds_end:
        write_bool(w, True)
        # timebounds are sent as uint32s since that's all we can display, but they must be hashed as 64bit
        write_uint64(w, msg.timebounds_start)
        write_uint64(w, msg.timebounds_end)
    else:
        write_bool(w, False)

    write_uint32(w, msg.memo_type)
    if msg.memo_type == 1:  # nothing is needed for memo_type = 0
        # Text: 4 bytes (size) + up to 28 bytes
        if len(msg.memo_text) > 28:
            raise ValueError('Stellar: max length of a memo text is 28 bytes')
        write_string(w, msg.memo_text)
    elif msg.memo_type == 2:
        # ID: 64 bit unsigned integer
        write_uint64(w, msg.memo_id)
    elif msg.memo_type in [3, 4]:
        # Hash/Return: 32 byte hash
        write_bytes(w, bytearray(msg.memo_hash))

    write_uint32(w, msg.num_operations)
    for i in range(msg.num_operations):
        op = yield StellarTxOpRequest()
        serialize_op(w, op)

    # 4 null bytes representing a (currently unused) empty union
    write_uint32(w, 0)

    # confirms
    await helpers.confirm_init(pubkey, msg.network_passphrase)
    await helpers.confirm_final(msg.fee, msg.num_operations)

    # sign
    # (note that the signature does not include the 4-byte hint since it can be calculated from the public key)
    digest = sha256(w).digest()
    signature = ed25519.sign(node.private_key(), digest)

    # Add the public key for verification that the right account was used for signing
    resp = StellarSignedTx()
    resp.public_key = pubkey
    resp.signature = signature

    yield resp


def node_derive(root, address_n: list):
    node = root.clone()
    node.derive_path(address_n)
    return node
