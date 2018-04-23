from .layout import *
from .serialize import *
from trezor.messages.NEMSignTx import NEMTransfer


async def transfer(ctx, public_key: bytes, common: NEMTransactionCommon, transfer: NEMTransfer, node):
    transfer.mosaics = canonicalize_mosaics(transfer.mosaics)

    payload, encrypted = get_transfer_payload(transfer, node)
    await ask_transfer(ctx, common, transfer, payload, encrypted)

    w = serialize_transfer(common, transfer, public_key, payload, encrypted)
    for mosaic in transfer.mosaics:
        serialize_mosaic(w, mosaic.namespace, mosaic.mosaic, mosaic.quantity)
    return w


async def importance_transfer(ctx, public_key: bytes, common: NEMTransactionCommon, imp: NEMImportanceTransfer):
    await ask_importance_transfer(ctx, common, imp)
    return serialize_importance_transfer(common, imp, public_key)
