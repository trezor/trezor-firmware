from trezor import wire
from trezor.crypto.curve import ed25519
from trezor.messages.NEMSignedTx import NEMSignedTx
from trezor.messages.NEMSignTx import NEMSignTx

from apps.common import seed
from apps.common.keychain import with_slip44_keychain
from apps.common.paths import validate_path
from apps.nem import CURVE, SLIP44_ID, mosaic, multisig, namespace, transfer
from apps.nem.helpers import NEM_HASH_ALG, check_path
from apps.nem.validators import validate


@with_slip44_keychain(SLIP44_ID, CURVE, allow_testnet=True)
async def sign_tx(ctx, msg: NEMSignTx, keychain):
    validate(msg)

    await validate_path(
        ctx,
        check_path,
        keychain,
        msg.transaction.address_n,
        CURVE,
        network=msg.transaction.network,
    )

    node = keychain.derive(msg.transaction.address_n)

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
        raise wire.DataError("No transaction provided")

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
