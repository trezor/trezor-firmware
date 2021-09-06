from trezor import wire
from trezor.crypto.curve import ed25519
from trezor.enums import LiskTransactionModuleID, MessageType
from trezor.messages import LiskSignedTx
from trezor.protobuf import dump_message_buffer, load_message_buffer

from apps.common import paths
from apps.common.keychain import auto_keychain

from . import layout
from .helpers import get_lisk32_from_address_hash


@auto_keychain(__name__)
async def sign_tx(ctx, msg, keychain):
    await paths.validate_path(ctx, keychain, msg.address_n)

    # decode the buffer into LiskTransaction
    tx = load_message_buffer(msg.transaction, MessageType.LiskTransaction)

    pubkey, seckey = _get_keys(keychain, msg)

    # check if the sender_public_key is the same as the derived one
    if not _check_sender_publick_key(tx, pubkey):
        raise wire.DataError("The transaction has invalid sender public key")

    # decode the asset based on module_id and asset_id
    asset = _decode_tx_asset(tx)
    # Reset asset with the dump (so we are sure we are signing only what we expect)
    tx.asset = dump_message_buffer(asset)

    try:
        await _require_confirm_by_type(ctx, tx, asset)
    except AttributeError:
        raise wire.DataError("The transaction has invalid asset field")

    amount = _get_tx_amount(tx, asset)
    await layout.require_confirm_fee(ctx, amount, tx.fee)

    txbytes = dump_message_buffer(tx)
    txbytes_to_sign = b"".join([msg.networkIdentifier, bytes(txbytes)])
    signature = ed25519.sign(seckey, txbytes_to_sign)

    return LiskSignedTx(signature=signature)


def _get_keys(keychain, msg):
    node = keychain.derive(msg.address_n)

    seckey = node.private_key()
    pubkey = node.public_key()
    pubkey = pubkey[1:]  # skip ed25519 pubkey marker

    return pubkey, seckey


def _check_sender_publick_key(tx, pubkey):
    return tx.sender_public_key == pubkey


def _decode_tx_asset(tx):

    if not tx.asset:
        raise wire.DataError("Missing asset data")

    # Module ID = 2 - Token
    if tx.module_id == LiskTransactionModuleID.Token:
        if tx.asset_id == 0:  # Transfer
            return load_message_buffer(tx.asset, MessageType.LiskAssetTransfer)
        else:
            raise wire.DataError("Invalid module type for Token module")
    # Module ID = 4 - Multisignature
    elif tx.module_id == LiskTransactionModuleID.Multisignature:
        if tx.asset_id == 0:  # Register Multisignature
            return load_message_buffer(tx.asset, MessageType.LiskAssetRegisterMultisig)
        else:
            raise wire.DataError("Invalid module type for Multisignature module")
    # Module ID = 5 - Dpos
    elif tx.module_id == LiskTransactionModuleID.Dpos:
        if tx.asset_id == 0:  # Register Delegate
            return load_message_buffer(tx.asset, MessageType.LiskAssetRegisterDelegate)
        elif tx.asset_id == 1:  # Vote Delegate
            return load_message_buffer(tx.asset, MessageType.LiskAssetVoteDelegate)
        elif tx.asset_id == 2:  # Unlock Token
            return load_message_buffer(tx.asset, MessageType.LiskAssetUnlockToken)
        else:
            raise wire.DataError("Invalid module type for Dpos module")
    # Module ID = 1000 - Legacy
    elif tx.module_id == LiskTransactionModuleID.Legacy:
        if tx.asset_id == 0:  # Reclaim Lisk
            return load_message_buffer(tx.asset, MessageType.LiskAssetReclaimLisk)
        else:
            raise wire.DataError("Invalid module type for Legacy module")
    else:
        raise wire.DataError("Invalid module type")


async def _require_confirm_by_type(ctx, tx, asset):
    # Transfer
    if tx.module_id == LiskTransactionModuleID.Token and tx.asset_id == 0:
        recipient_address = get_lisk32_from_address_hash(asset.recipient_address)
        await layout.require_confirm_tx(ctx, recipient_address, asset.amount)
        if asset.data != "":
            await layout.require_confirm_data(ctx, asset.data)
        return
    # Register Multisignature
    elif tx.module_id == LiskTransactionModuleID.Multisignature and tx.asset_id == 0:
        return await layout.require_confirm_multisig_tx(ctx, asset)
    # Register Delegate
    elif tx.module_id == LiskTransactionModuleID.Dpos and tx.asset_id == 0:
        return await layout.require_confirm_delegate_registration(ctx, asset.username)
    # Vote Delegate
    elif tx.module_id == LiskTransactionModuleID.Dpos and tx.asset_id == 1:
        return await layout.require_confirm_vote_tx(ctx, asset.votes)
    # Unlock Token
    elif tx.module_id == LiskTransactionModuleID.Dpos and tx.asset_id == 2:
        return await layout.require_confirm_unlock_tx(ctx, asset.unlock_objects)
    # Reclaim Lisk
    elif tx.module_id == LiskTransactionModuleID.Legacy and tx.asset_id == 0:
        return await layout.require_confirm_reclaim_tx(ctx, asset.amount)
    else:
        raise wire.DataError("Unexpected error")


def _get_tx_amount(tx, asset):
    # Transfer
    if tx.module_id == LiskTransactionModuleID.Token and tx.asset_id == 0:
        return asset.amount
    # Reclaim Lisk
    elif tx.module_id == LiskTransactionModuleID.Legacy and tx.asset_id == 0:
        return asset.amount
    # All the others
    else:
        return 0
