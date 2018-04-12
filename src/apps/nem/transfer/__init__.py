from .layout import *
from .serialize import *


async def transfer(ctx, public_key: bytes, msg: NEMSignTx, node):
    msg.transfer.mosaics = canonicalize_mosaics(msg.transfer.mosaics)

    payload, encrypted = get_transfer_payload(msg, node)
    await ask_transfer(ctx, msg, payload, encrypted)

    w = serialize_transfer(msg, public_key, payload, encrypted)
    for mosaic in msg.transfer.mosaics:
        serialize_mosaic(w, mosaic.namespace, mosaic.mosaic, mosaic.quantity)
    return w


async def importance_transfer(ctx, public_key: bytes, msg: NEMSignTx):
    await ask_importance_transfer(ctx, msg)
    return serialize_importance_transfer(msg, public_key)
