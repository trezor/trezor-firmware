from trezor import wire, ui
from trezor.messages.LiskSignedTx import LiskSignedTx
from trezor.messages.LiskTransactionType import *
from trezor.messages import FailureType
from trezor.utils import HashWriter
from apps.lisk.layout import *
from ubinascii import unhexlify, hexlify


async def lisk_sign_tx(ctx, msg):
    from trezor.crypto.hashlib import sha256

    pubkey, seckey = await _get_keys(ctx, msg)
    transaction = update_raw_tx(msg.transaction, pubkey)

    # throw ValueError if transaction has not valid structure
    try:
        await require_confirm_by_type(ctx, transaction)
    except AttributeError:
        raise ValueError(FailureType.DataError, 'The transaction has invalid asset data field')

    await require_confirm_fee(ctx, transaction.amount, transaction.fee)

    sha = HashWriter(sha256)
    transaction_bytes = _get_transaction_bytes(transaction)

    for field in transaction_bytes:
        sha.extend(field)

    digest = sha.get_digest()

    signature = await get_signature(seckey, digest)

    return LiskSignedTx(signature=signature)

async def require_confirm_by_type(ctx, transaction):
    if transaction.type == Transfer:
        return await require_confirm_tx(ctx, transaction.recipient_id, transaction.amount)
    if transaction.type == RegisterDelegate:
        return await require_confirm_delegate_registration(ctx, transaction.asset.delegate.username)
    if transaction.type == CastVotes:
        return await require_confirm_vote_tx(ctx, transaction.asset.votes)
    if transaction.type == RegisterSecondPassphrase:
        return await require_confirm_public_key(ctx, transaction.asset.signature.public_key)
    if transaction.type == RegisterMultisignatureAccount:
        return await require_confirm_multisig(ctx, transaction.asset.multisignature)
    raise ValueError(FailureType.DataError, 'Invalid transaction type')

async def get_signature(seckey, digest):
    from trezor.crypto.curve import ed25519
    signature = ed25519.sign(seckey, digest)

    return signature

def _get_transaction_bytes(msg):
    from ustruct import pack

    # Required transaction parameters
    t_type = pack('<b', msg.type)
    t_timestamp = pack('<i', msg.timestamp)
    t_amount = pack('<Q', msg.amount)
    t_pubkey = msg.sender_public_key

    t_requester_public_key = msg.requester_public_key or b''

    # Value can be empty string
    if not msg.recipient_id:
        t_recipient_id = pack('>Q', 0)
    else:
        # Lisk use big-endian for recipient_id
        # string -> int -> bytes
        t_recipient_id = pack('>Q', int(msg.recipient_id[:-1]))

    t_signature = msg.signature or b''

    t_asset = _get_asset_data_bytes(msg)

    return t_type, t_timestamp, t_pubkey, t_requester_public_key, t_recipient_id, t_amount, t_asset, t_signature

def _get_asset_data_bytes(msg):
    from ustruct import pack

    if msg.type == Transfer:
        # Transfer transaction have optional data field
        if msg.asset.data is not None:
            return bytes(msg.asset.data, "utf8")
        else:
            return b''

    if msg.type == RegisterDelegate:
        return bytes(msg.asset.delegate.username, "utf8")

    if msg.type == CastVotes:
        return bytes("".join(msg.asset.votes), "utf8")

    if msg.type == RegisterSecondPassphrase:
        return msg.asset.signature.public_key

    if msg.type == RegisterMultisignatureAccount:
        data = b''
        data += pack('<b', msg.asset.multisignature.min)
        data += pack('<b', msg.asset.multisignature.life_time)
        data += bytes("".join(msg.asset.multisignature.keys_group), "utf8")
        return data

async def _get_keys(ctx, msg):
    from ..common import seed
    from .helpers import LISK_CURVE

    address_n = msg.address_n or ()
    node = await seed.derive_node(ctx, address_n, LISK_CURVE)

    seckey = node.private_key()
    pubkey = node.public_key()
    pubkey = pubkey[1:]  # skip ed25519 pubkey marker

    return pubkey, seckey

def update_raw_tx(transaction, pubkey):
    from .helpers import get_address_from_public_key

    transaction.sender_public_key = pubkey

    # For this type of transactions, recipientId should be equal transaction creator address.
    if transaction.type == CastVotes:
        transaction.recipient_id = get_address_from_public_key(pubkey)

    return transaction
