from trezor.messages.NEM2TransactionCommon import NEM2TransactionCommon
from trezor.messages.NEM2NamespaceRegistrationTransaction import NEM2NamespaceRegistrationTransaction
from trezor.messages.NEM2AddressAliasTransaction import NEM2AddressAliasTransaction

from . import layout, serialize

async def namespace_registration(
    ctx,
    common: NEM2TransactionCommon,
    namespace_registration: NEM2NamespaceRegistrationTransaction
):

    await layout.ask_namespace_registration(ctx, common, namespace_registration)

    return serialize.serialize_namespace_registration(common, namespace_registration)

async def address_alias(
    ctx,
    common: NEM2TransactionCommon,
    address_alias: NEM2AddressAliasTransaction
):

    await layout.ask_address_alias(ctx, common, address_alias)

    return serialize.serialize_address_alias(common, address_alias)

async def mosaic_alias(
    ctx, common: NEM2TransactionCommon, creation: NEM2MosaicAliasTransaction
) -> bytearray:
    await layout.ask_mosaic_alias(ctx, common, creation)
    return serialize.serialize_mosaic_alias(common, creation)
