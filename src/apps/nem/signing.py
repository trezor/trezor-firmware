from trezor.crypto.curve import ed25519
from trezor.messages.NEMSignedTx import NEMSignedTx
from trezor.messages.NEMSignTx import NEMSignTx

from . import mosaic, multisig, namespace, transfer
from .helpers import NEM_CURVE, NEM_HASH_ALG
from .validators import validate

from apps.common import seed


async def sign_tx(ctx, msg: NEMSignTx):
    validate(msg)
    node = await seed.derive_node(ctx, msg.transaction.address_n, NEM_CURVE)

    if msg.multisig:
        public_key = msg.multisig.signer
        common = msg.multisig
        await multisig.ask(ctx, msg)
    else:
        public_key = seed.remove_ed25519_prefix(node.public_key())
        common = msg.transaction

    if msg.transfer:
        tx = await transfer.transfer(ctx, public_key, common, msg.transfer, node)
    elif msg.provision_namespace:
        tx = await namespace.namespace(ctx, public_key, common, msg.provision_namespace)
    elif msg.mosaic_creation:
        tx = await mosaic.mosaic_creation(ctx, public_key, common, msg.mosaic_creation)
    elif msg.supply_change:
        tx = await mosaic.supply_change(ctx, public_key, common, msg.supply_change)
    elif msg.aggregate_modification:
        tx = await multisig.aggregate_modification(
            ctx,
            public_key,
            common,
            msg.aggregate_modification,
            msg.multisig is not None,
        )
    elif msg.importance_transfer:
        tx = await transfer.importance_transfer(
            ctx, public_key, common, msg.importance_transfer
        )
    else:
        raise ValueError("No transaction provided")

    if msg.multisig:
        # wrap transaction in multisig wrapper
        if msg.cosigning:
            tx = multisig.cosign(
                seed.remove_ed25519_prefix(node.public_key()),
                msg.transaction,
                tx,
                msg.multisig.signer,
            )
        else:
            tx = multisig.initiate(
                seed.remove_ed25519_prefix(node.public_key()), msg.transaction, tx
            )

    signature = ed25519.sign(node.private_key(), tx, NEM_HASH_ALG)

    resp = NEMSignedTx()
    resp.data = tx
    resp.signature = signature
    return resp
