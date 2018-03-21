from apps.nem.transaction import *
from apps.nem.layout import *
from apps.nem import helpers
from apps.common import seed
from trezor.messages.NEMSignTx import NEMSignTx
from trezor.messages.NEMSignedTx import NEMSignedTx
from trezor.crypto.curve import ed25519
from trezor.crypto import random


async def nem_sign_tx(ctx, msg: NEMSignTx):

    node = await seed.derive_node(ctx, msg.transaction.address_n, NEM_CURVE)

    payload = msg.transfer.payload
    encrypted = False
    if msg.transfer.public_key is not None:
        if payload is None:
            raise ValueError("Public key provided but no payload to encrypt")
        payload = _nem_encrypt(node, msg.transfer.public_key, msg.transfer.payload)
        encrypted = True

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
        payload,
        encrypted,
        len(msg.transfer.mosaics)
    )

    for mosaic in msg.transfer.mosaics:
        nem_transaction_write_mosaic(tx, mosaic.namespace, mosaic.mosaic, mosaic.quantity)

    if payload:  # confirm unencrypted
        # todo encrypted vs unencrypted
        await require_confirm_action(ctx)  # todo

    await require_confirm_fee(ctx, msg.transfer.amount, msg.transaction.fee)  # todo
    await require_confirm_tx(ctx, msg.transfer.recipient, msg.transfer.amount)  # todo

    signature = ed25519.sign(node.private_key(), tx, helpers.NEM_HASH_ALG)

    resp = NEMSignedTx()
    resp.data = tx
    resp.signature = signature
    return resp


def _nem_encrypt(node, public_key: bytes, payload: bytes) -> bytes:
    salt = random.bytes(helpers.NEM_SALT_SIZE)
    iv = random.bytes(helpers.AES_BLOCK_SIZE)
    encrypted = node.nem_encrypt(public_key, iv, salt, payload)
    return iv + salt + encrypted
