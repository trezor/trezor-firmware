from typing import TYPE_CHECKING

from . import layout, serialize

if TYPE_CHECKING:
    from trezor.crypto import bip32
    from trezor.messages import NEMImportanceTransfer, NEMTransactionCommon, NEMTransfer


async def transfer(
    public_key: bytes,
    common: NEMTransactionCommon,
    transfer: NEMTransfer,
    node: bip32.HDNode,
    chunkify: bool,
) -> bytes:
    transfer.mosaics = serialize.canonicalize_mosaics(transfer.mosaics)
    payload, encrypted = serialize.get_transfer_payload(transfer, node)

    await layout.ask_transfer(common, transfer, encrypted, chunkify)

    w = serialize.serialize_transfer(common, transfer, public_key, payload, encrypted)
    for mosaic in transfer.mosaics:
        serialize.serialize_mosaic(w, mosaic.namespace, mosaic.mosaic, mosaic.quantity)
    return w


async def importance_transfer(
    public_key: bytes,
    common: NEMTransactionCommon,
    imp: NEMImportanceTransfer,
) -> bytes:
    await layout.ask_importance_transfer(common, imp)
    return serialize.serialize_importance_transfer(common, imp, public_key)
