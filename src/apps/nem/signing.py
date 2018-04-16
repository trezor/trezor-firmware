from apps.nem import namespace
from apps.nem import transfer
from apps.nem import mosaic
from apps.nem import multisig
from apps.nem.validators import validate
from apps.nem.helpers import *
from apps.common import seed
from trezor.messages.NEMSignTx import NEMSignTx
from trezor.messages.NEMSignedTx import NEMSignedTx
from trezor.crypto.curve import ed25519


async def sign_tx(ctx, msg: NEMSignTx):
    validate(msg)
    node = await seed.derive_node(ctx, msg.transaction.address_n, NEM_CURVE)

    if msg.multisig:
        public_key = msg.multisig.signer
        await multisig.ask(ctx, msg)
    else:
        public_key = _get_public_key(node)

    if msg.transfer:
        tx = await transfer.transfer(ctx, public_key, msg, node)
    elif msg.provision_namespace:
        tx = await namespace.namespace(ctx, public_key, msg)
    elif msg.mosaic_creation:
        tx = await mosaic.mosaic_creation(ctx, public_key, msg)
    elif msg.supply_change:
        tx = await mosaic.supply_change(ctx, public_key, msg)
    elif msg.aggregate_modification:
        tx = await multisig.aggregate_modification(ctx, public_key, msg)
    elif msg.importance_transfer:
        tx = await transfer.importance_transfer(ctx, public_key, msg)
    else:
        raise ValueError('No transaction provided')

    if msg.multisig:
        # wrap transaction in multisig wrapper
        if msg.cosigning:
            tx = multisig.cosign(_get_public_key(node), msg.transaction, tx, msg.multisig.signer)
        else:
            tx = multisig.initiate(_get_public_key(node), msg.transaction, tx)

    signature = ed25519.sign(node.private_key(), tx, NEM_HASH_ALG)

    resp = NEMSignedTx()
    resp.data = tx
    resp.signature = signature
    return resp


def _get_public_key(node) -> bytes:
    # 0x01 prefix is not part of the actual public key, hence removed
    return node.public_key()[1:]
