from trezor.messages.NEM2TransactionCommon import NEM2TransactionCommon
from trezor.messages.NEM2NamespaceMetadataTransaction import NEM2NamespaceMetadataTransaction

from . import layout, serialize

async def namespace_metadata(
    ctx,
    common: NEM2TransactionCommon,
    namespace_metadata: NEM2NamespaceMetadataTransaction
):

    await layout.ask_namespace_metadata(ctx, common, namespace_metadata)

    return serialize.serialize_namespace_metadata(common, namespace_metadata)

