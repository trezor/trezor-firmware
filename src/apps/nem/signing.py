from apps.nem.transaction import *
from apps.nem.layout import *
from trezor.messages.NEMSignTx import NEMSignTx
from trezor.messages.NEMSignedTx import NEMSignedTx


async def nem_sign_tx(ctx, msg: NEMSignTx):
    from ..common import seed
    from trezor.crypto.curve import ed25519

    # if len(msg.transfer.public_key):
        # todo encrypt

    node = await seed.derive_node(ctx, msg.transaction.address_n, NEM_CURVE)
    # 0x01 prefix is not part of the actual public key, hence removed
    public_key = node.public_key()[1:]

    tx = nem_transaction_create_transfer(
        msg.transaction.network,
        msg.transaction.timestamp,
        public_key,
        msg.transaction.fee,
        msg.transaction.deadline,
        msg.transfer.recipient,
        msg.transfer.amount,
        msg.transfer.payload,  # todo might require encryption
        msg.transfer.public_key is not None,
        len(msg.transfer.mosaics)
    )

    for mosaic in msg.transfer.mosaics:
        nem_transaction_write_mosaic(tx, mosaic.namespace, mosaic.mosaic, mosaic.quantity)

    await require_confirm_action(ctx)
    await require_confirm_fee(ctx, msg.transfer.amount, msg.transaction.fee)
    await require_confirm_tx(ctx, msg.transfer.recipient, msg.transfer.amount)

    signature = ed25519.sign(node.private_key(), tx, 'keccak')

    resp = NEMSignedTx()
    resp.data = tx
    resp.signature = signature
    return resp
