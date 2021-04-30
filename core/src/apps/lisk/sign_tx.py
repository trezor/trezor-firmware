import ustruct

from trezor import wire
from trezor.crypto.curve import ed25519
from trezor.crypto.hashlib import sha256
from trezor.messages import LiskSignedTx, LiskTransactionType
from trezor.utils import HashWriter

from apps.common import paths
from apps.common.keychain import auto_keychain

from . import layout
from .helpers import get_address_from_public_key


@auto_keychain(__name__)
async def sign_tx(ctx, msg, keychain):
    await paths.validate_path(ctx, keychain, msg.address_n)

    pubkey, seckey = _get_keys(keychain, msg)
    transaction = _update_raw_tx(msg.transaction, pubkey)

    try:
        await _require_confirm_by_type(ctx, transaction)
    except AttributeError:
        raise wire.DataError("The transaction has invalid asset data field")

    await layout.require_confirm_fee(ctx, transaction.amount, transaction.fee)

    txbytes = _get_transaction_bytes(transaction)
    txhash = HashWriter(sha256())
    for field in txbytes:
        txhash.extend(field)
    digest = txhash.get_digest()

    signature = ed25519.sign(seckey, digest)

    return LiskSignedTx(signature=signature)


def _get_keys(keychain, msg):
    node = keychain.derive(msg.address_n)

    seckey = node.private_key()
    pubkey = node.public_key()
    pubkey = pubkey[1:]  # skip ed25519 pubkey marker

    return pubkey, seckey


def _update_raw_tx(transaction, pubkey):
    # If device is using for second signature sender_public_key must be exist in transaction
    if not transaction.sender_public_key:
        transaction.sender_public_key = pubkey

    # For CastVotes transactions, recipientId should be equal to transaction
    # creator address.
    if transaction.type == LiskTransactionType.CastVotes:
        if not transaction.recipient_id:
            transaction.recipient_id = get_address_from_public_key(pubkey)

    return transaction


async def _require_confirm_by_type(ctx, transaction):

    if transaction.type == LiskTransactionType.Transfer:
        return await layout.require_confirm_tx(
            ctx, transaction.recipient_id, transaction.amount
        )

    if transaction.type == LiskTransactionType.RegisterDelegate:
        return await layout.require_confirm_delegate_registration(
            ctx, transaction.asset.delegate.username
        )

    if transaction.type == LiskTransactionType.CastVotes:
        return await layout.require_confirm_vote_tx(ctx, transaction.asset.votes)

    if transaction.type == LiskTransactionType.RegisterSecondPassphrase:
        return await layout.require_confirm_public_key(
            ctx, transaction.asset.signature.public_key
        )

    if transaction.type == LiskTransactionType.RegisterMultisignatureAccount:
        return await layout.require_confirm_multisig(
            ctx, transaction.asset.multisignature
        )

    raise wire.DataError("Invalid transaction type")


def _get_transaction_bytes(tx):

    # Required transaction parameters
    t_type = ustruct.pack("<b", tx.type)
    t_timestamp = ustruct.pack("<i", tx.timestamp)
    t_sender_public_key = tx.sender_public_key
    t_requester_public_key = tx.requester_public_key or b""

    if not tx.recipient_id:
        # Value can be empty string
        t_recipient_id = ustruct.pack(">Q", 0)
    else:
        # Lisk uses big-endian for recipient_id, string -> int -> bytes
        t_recipient_id = ustruct.pack(">Q", int(tx.recipient_id[:-1]))

    t_amount = ustruct.pack("<Q", tx.amount)
    t_asset = _get_asset_data_bytes(tx)
    t_signature = tx.signature or b""

    return (
        t_type,
        t_timestamp,
        t_sender_public_key,
        t_requester_public_key,
        t_recipient_id,
        t_amount,
        t_asset,
        t_signature,
    )


def _get_asset_data_bytes(msg):

    if msg.type == LiskTransactionType.Transfer:
        # Transfer transaction have optional data field
        if msg.asset.data is not None:
            return msg.asset.data.encode()
        else:
            return b""

    if msg.type == LiskTransactionType.RegisterDelegate:
        return msg.asset.delegate.username.encode()

    if msg.type == LiskTransactionType.CastVotes:
        return ("".join(msg.asset.votes)).encode()

    if msg.type == LiskTransactionType.RegisterSecondPassphrase:
        return msg.asset.signature.public_key

    if msg.type == LiskTransactionType.RegisterMultisignatureAccount:
        data = b""
        data += ustruct.pack("<b", msg.asset.multisignature.min)
        data += ustruct.pack("<b", msg.asset.multisignature.life_time)
        data += ("".join(msg.asset.multisignature.keys_group)).encode()
        return data

    raise wire.DataError("Invalid transaction type")
