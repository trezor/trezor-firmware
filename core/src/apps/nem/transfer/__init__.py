from trezor.messages import NEMImportanceTransfer, NEMTransactionCommon, NEMTransfer

from . import layout, serialize

if False:
    from trezor.wire import Context
    from trezor.crypto import bip32


async def transfer(
    ctx: Context,
    public_key: bytes,
    common: NEMTransactionCommon,
    transfer: NEMTransfer,
    node: bip32.HDNode,
) -> bytes:
    transfer.mosaics = serialize.canonicalize_mosaics(transfer.mosaics)
    payload, is_encrypted = serialize.get_transfer_payload(transfer, node)

    await layout.ask_transfer(ctx, common, transfer, is_encrypted)

    w = serialize.serialize_transfer(
        common, transfer, public_key, payload, is_encrypted
    )
    for mosaic in transfer.mosaics:
        serialize.serialize_mosaic(w, mosaic.namespace, mosaic.mosaic, mosaic.quantity)
    return w


async def importance_transfer(
    ctx: Context,
    public_key: bytes,
    common: NEMTransactionCommon,
    imp: NEMImportanceTransfer,
) -> bytes:
    await layout.ask_importance_transfer(ctx, common, imp)
    return serialize.serialize_importance_transfer(common, imp, public_key)
