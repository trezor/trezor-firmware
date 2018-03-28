from apps.nem.layout import *
from apps.nem.transaction import *
from apps.nem.validators import validate
from apps.nem import helpers
from apps.common import seed
from trezor.messages.NEMSignTx import NEMSignTx
from trezor.messages.NEMSignedTx import NEMSignedTx
from trezor.crypto.curve import ed25519
from trezor.crypto import random


async def nem_sign_tx(ctx, msg: NEMSignTx):
    validate(msg)
    node = await seed.derive_node(ctx, msg.transaction.address_n, NEM_CURVE)
    tx = bytearray()

    if msg.transfer:
        tx = await _transfer(ctx, node, msg)
        # todo msg.transfer.mosaics = canonicalize_mosaics(msg.transfer.mosaics)

    elif msg.provision_namespace:  # todo are those disjunctive?
        tx = await _provision_namespace(ctx, node, msg)

    signature = ed25519.sign(node.private_key(), tx, helpers.NEM_HASH_ALG)

    resp = NEMSignedTx()
    resp.data = tx
    resp.signature = signature
    return resp


async def _provision_namespace(ctx, node, msg: NEMSignTx) -> bytearray:
    await require_confirm_fee(ctx, msg.transaction.fee)
    await require_confirm_final(ctx, 'Create provision namespace "' + msg.provision_namespace.namespace + '"?')
    return nem_transaction_create_provision_namespace(
        msg.transaction.network,
        msg.transaction.timestamp,
        _get_public_key(node),
        msg.transaction.fee,
        msg.transaction.deadline,
        msg.provision_namespace.namespace,
        msg.provision_namespace.parent,
        msg.provision_namespace.sink,
        msg.provision_namespace.fee)


async def _transfer(ctx, node, msg: NEMSignTx) -> bytes:
    payload, encrypted = _get_payload(msg, node)
    tx = nem_transaction_create_transfer(
        msg.transaction.network,
        msg.transaction.timestamp,
        _get_public_key(node),
        msg.transaction.fee,
        msg.transaction.deadline,
        msg.transfer.recipient,
        msg.transfer.amount,
        payload,
        encrypted,
        len(msg.transfer.mosaics)
    )

    for mosaic in msg.transfer.mosaics:
        nem_transaction_write_mosaic(tx, mosaic.namespace, mosaic.mosaic, mosaic.quantity)

    if payload:  # confirm unencrypted
        await require_confirm_payload(ctx, msg.transfer.payload, encrypted)

    await require_confirm_fee(ctx, msg.transaction.fee)
    await require_confirm_tx(ctx, msg.transfer.recipient, msg.transfer.amount)

    return tx


def _get_payload(msg: NEMSignTx, node) -> [bytes, bool]:
    payload = msg.transfer.payload
    encrypted = False
    if msg.transfer.public_key is not None:
        if payload is None:
            raise ValueError("Public key provided but no payload to encrypt")
        payload = _nem_encrypt(node, msg.transfer.public_key, msg.transfer.payload)
        encrypted = True

    return payload, encrypted


def _get_public_key(node) -> bytes:
    # 0x01 prefix is not part of the actual public key, hence removed
    return node.public_key()[1:]


def _nem_encrypt(node, public_key: bytes, payload: bytes) -> bytes:
    salt = random.bytes(helpers.NEM_SALT_SIZE)
    iv = random.bytes(helpers.AES_BLOCK_SIZE)
    encrypted = node.nem_encrypt(public_key, iv, salt, payload)
    return iv + salt + encrypted
