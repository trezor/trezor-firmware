from trezor.messages.StellarAccountMergeOp import StellarAccountMergeOp
from trezor.messages.StellarSignTx import StellarSignTx
from trezor.messages.StellarTxOpRequest import StellarTxOpRequest
from trezor.messages.StellarSignedTx import StellarSignedTx
from trezor.messages import wire_types
from .writers import *
from ..common import seed
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
            res = await ctx.call(req, wire_types.StellarAccountMergeOp)
        elif isinstance(req, StellarSignedTx):
            break
        else:
            raise TypeError('Invalid Stellar signing instruction')
    return req


async def sign_tx(ctx, msg):
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
        write_bytes(w, bytearray(msg.memo_text))  # todo trim to 28 bytes? yes max 28 bytes!
    elif msg.memo_type == 2:
        # ID: 64 bit unsigned integer
        write_uint64(w, msg.memo_id)
    elif msg.memo_type in [3, 4]:
        # Hash/Return: 32 byte hash
        write_bytes(w, bytearray(msg.memo_hash))

    write_uint32(w, msg.num_operations)
    for i in range(msg.num_operations):
        op = yield StellarTxOpRequest()
        # todo ask
        # todo serialize OP
        if isinstance(op, StellarAccountMergeOp):
            serialize_account_merge_op(w, op)

    # # Determine what type of network this transaction is for  - todo used for layout
    # if msg.network_passphrase == "Public Global Stellar Network ; September 2015":
    #     network_type = 1
    # elif msg.network_passphrase == "Test SDF Network ; September 2015":
    #     network_type = 2
    # else:
    #     network_type = 3
    # # todo use network_type in layout

    # 4 null bytes representing a (currently unused) empty union
    write_uint32(w, 0)

    # sign
    # (note that the signature does not include the 4-byte hint since it can be calculated from the public key)
    digest = sha256(w).digest()
    signature = ed25519.sign(node.private_key(), digest)

    # Add the public key for verification that the right account was used for signing
    resp = StellarSignedTx()
    resp.public_key = pubkey
    resp.signature = signature

    yield resp


def serialize_account_merge_op(w, msg: StellarAccountMergeOp):
    if not msg.source_account:
        write_bool(w, False)  # todo move this to stellar_confirmSourceAccount
    #else: todo ask and hash the address
    write_uint32(w, 8)  # merge op todo
    write_pubkey(w, msg.destination_account)


def node_derive(root, address_n: list):
    node = root.clone()
    node.derive_path(address_n)
    return node
