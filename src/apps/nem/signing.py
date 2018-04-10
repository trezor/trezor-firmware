from apps.nem.transfer import *
from apps.nem.multisig import *
from apps.nem.namespace import *
from apps.nem.mosaic import *
from apps.nem.validators import validate
from apps.nem import helpers
from apps.common import seed
from trezor.messages.NEMSignTx import NEMSignTx
from trezor.messages.NEMSignedTx import NEMSignedTx
from trezor.crypto.curve import ed25519


async def sign_tx(ctx, msg: NEMSignTx):
    validate(msg)
    node = await seed.derive_node(ctx, msg.transaction.address_n, NEM_CURVE)

    if msg.multisig:
        public_key = msg.multisig.signer
        await ask_multisig(ctx, msg)
    else:
        public_key = _get_public_key(node)

    if msg.transfer:
        msg.transfer.mosaics = canonicalize_mosaics(msg.transfer.mosaics)
        tx = await _transfer(ctx, public_key, msg, node)
    elif msg.provision_namespace:
        tx = await _provision_namespace(ctx, public_key, msg)
    elif msg.mosaic_creation:
        tx = await _mosaic_creation(ctx, public_key, msg)
    elif msg.supply_change:
        tx = await _supply_change(ctx, public_key, msg)
    elif msg.aggregate_modification:
        tx = await _aggregate_modification(ctx, public_key, msg)
    elif msg.importance_transfer:
        tx = await _importance_transfer(ctx, public_key, msg)
    else:
        raise ValueError('No transaction provided')

    if msg.multisig:
        # wrap transaction in multisig wrapper
        tx = _multisig(node, msg, tx)

    signature = ed25519.sign(node.private_key(), tx, helpers.NEM_HASH_ALG)

    resp = NEMSignedTx()
    resp.data = tx
    resp.signature = signature
    return resp


def _multisig(node, msg: NEMSignTx, inner_tx: bytes) -> bytes:
    if msg.cosigning:
        return serialize_multisig_signature(msg.multisig,
                                            _get_public_key(node),
                                            inner_tx,
                                            msg.multisig.signer)
    else:
        return serialize_multisig(msg.multisig, _get_public_key(node), inner_tx)


def _get_public_key(node) -> bytes:
    # 0x01 prefix is not part of the actual public key, hence removed
    return node.public_key()[1:]


async def _transfer(ctx, public_key: bytes, msg: NEMSignTx, node) -> bytes:
    payload, encrypted = get_transfer_payload(msg, node)
    await ask_transfer(ctx, msg, payload, encrypted)

    w = serialize_transfer(msg, public_key, payload, encrypted)
    for mosaic in msg.transfer.mosaics:
        serialize_mosaic(w, mosaic.namespace, mosaic.mosaic, mosaic.quantity)
    return w


async def _provision_namespace(ctx, public_key: bytes, msg: NEMSignTx) -> bytearray:
    await ask_provision_namespace(ctx, msg)
    return serialize_provision_namespace(msg, public_key)


async def _mosaic_creation(ctx, public_key: bytes, msg: NEMSignTx) -> bytearray:
    await ask_mosaic_creation(ctx, msg)
    return serialize_mosaic_creation(msg, public_key)


async def _supply_change(ctx, public_key: bytes, msg: NEMSignTx):
    await ask_mosaic_supply_change(ctx, msg)
    return serialize_mosaic_supply_change(msg, public_key)


async def _aggregate_modification(ctx, public_key: bytes, msg: NEMSignTx):
    await ask_aggregate_modification(ctx, msg)
    w = serialize_aggregate_modification(msg, public_key)

    for m in msg.aggregate_modification.modifications:
        serialize_cosignatory_modification(w, m.type, m.public_key)

    if msg.aggregate_modification.relative_change:
        serialize_minimum_cosignatories(w, msg.aggregate_modification.relative_change)
    return w


async def _importance_transfer(ctx, public_key: bytes, msg: NEMSignTx):
    await ask_importance_transfer(ctx, msg)
    return serialize_importance_transfer(msg, public_key)
