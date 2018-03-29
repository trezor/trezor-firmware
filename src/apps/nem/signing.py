from apps.nem.layout import *
from apps.nem.transaction import *
from apps.nem.mosaic import *
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

    if msg.transfer:
        tx = await _transfer(ctx, node, msg)
        # todo msg.transfer.mosaics = canonicalize_mosaics(msg.transfer.mosaics)
    elif msg.provision_namespace:
        tx = await _provision_namespace(ctx, node, msg)
    elif msg.mosaic_creation:
        tx = await _mosaic_creation(ctx, node, msg)
    elif msg.supply_change:
        tx = await _supply_change(ctx, node, msg)
    elif msg.aggregate_modification:
        tx = await _aggregate_modification(ctx, node, msg)
    elif msg.importance_transfer:
        tx = await _importance_transfer(ctx, node, msg)
    else:
        raise ValueError('No transaction provided')

    signature = ed25519.sign(node.private_key(), tx, helpers.NEM_HASH_ALG)

    resp = NEMSignedTx()
    resp.data = tx
    resp.signature = signature
    return resp


async def _importance_transfer(ctx, node, msg: NEMSignTx):
    # todo confirms!
    w = nem_transaction_create_importance_transfer(
        msg.transaction.network,
        msg.transaction.timestamp,
        _get_public_key(node),
        msg.transaction.fee,
        msg.transaction.deadline,
        msg.importance_transfer.mode,
        msg.importance_transfer.public_key
    )
    return w


async def _aggregate_modification(ctx, node, msg: NEMSignTx):
    # todo confirms!
    w = nem_transaction_create_aggregate_modification(
        msg.transaction.network,
        msg.transaction.timestamp,
        _get_public_key(node),
        msg.transaction.fee,
        msg.transaction.deadline,
        len(msg.aggregate_modification.modifications),
        msg.aggregate_modification.relative_change
    )

    for m in msg.aggregate_modification.modifications:
        nem_transaction_write_cosignatory_modification(w, m.type, m.public_key)

    if msg.aggregate_modification.relative_change:
        nem_transaction_write_minimum_cosignatories(w, msg.aggregate_modification.relative_change)

    return w


async def _supply_change(ctx, node, msg: NEMSignTx):
    # todo confirms!
    return nem_transaction_create_mosaic_supply_change(
        msg.transaction.network,
        msg.transaction.timestamp,
        _get_public_key(node),
        msg.transaction.fee,
        msg.transaction.deadline,
        msg.supply_change.namespace,
        msg.supply_change.mosaic,
        msg.supply_change.type,
        msg.supply_change.delta
    )


async def _mosaic_creation(ctx, node, msg: NEMSignTx) -> bytearray:
    await require_confirm_action(ctx, 'Create mosaic "' + msg.mosaic_creation.definition.mosaic + '" under  namespace "'
                                 + msg.mosaic_creation.definition.namespace + '"?')
    # todo confirm levy!
    await require_confirm_properties(ctx, msg.mosaic_creation.definition)
    await require_confirm_final(ctx, 'mosaic', msg.transaction.fee)

    return nem_transaction_create_mosaic_creation(
        msg.transaction.network,
        msg.transaction.timestamp,
        _get_public_key(node),
        msg.transaction.fee,
        msg.transaction.deadline,
        msg.mosaic_creation.definition.namespace,
        msg.mosaic_creation.definition.mosaic,
        msg.mosaic_creation.definition.description,
        msg.mosaic_creation.definition.divisibility,
        msg.mosaic_creation.definition.supply,
        msg.mosaic_creation.definition.mutable_supply,
        msg.mosaic_creation.definition.transferable,
        msg.mosaic_creation.definition.levy,
        msg.mosaic_creation.definition.fee,
        msg.mosaic_creation.definition.levy_address,
        msg.mosaic_creation.definition.levy_namespace,
        msg.mosaic_creation.definition.levy_mosaic,
        msg.mosaic_creation.sink,
        msg.mosaic_creation.fee)


async def _provision_namespace(ctx, node, msg: NEMSignTx) -> bytearray:
    await require_confirm_action(ctx, 'Create provision namespace "' + msg.provision_namespace.namespace + '"?')
    await require_confirm_final(ctx, 'provision namespace', msg.transaction.fee)
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

    await require_confirm_action(ctx, 'todo')  # todo!
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
