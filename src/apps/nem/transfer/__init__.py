from trezor.messages.NEMTransfer import NEMTransfer
from trezor.messages.NEMTransactionCommon import NEMTransactionCommon
from trezor.messages.NEMImportanceTransfer import NEMImportanceTransfer

from . import layout, serialize


async def transfer(ctx, public_key: bytes, common: NEMTransactionCommon, transfer: NEMTransfer, node):
    transfer.mosaics = serialize.canonicalize_mosaics(transfer.mosaics)
    payload, encrypted = serialize.get_transfer_payload(transfer, node)

    await layout.ask_transfer(ctx, common, transfer, payload, encrypted)

    w = serialize.serialize_transfer(common, transfer, public_key, payload, encrypted)
    for mosaic in transfer.mosaics:
        serialize.serialize_mosaic(w, mosaic.namespace, mosaic.mosaic, mosaic.quantity)
    return w


async def importance_transfer(ctx, public_key: bytes, common: NEMTransactionCommon, imp: NEMImportanceTransfer):
    await layout.ask_importance_transfer(ctx, common, imp)
    return serialize.serialize_importance_transfer(common, imp, public_key)
