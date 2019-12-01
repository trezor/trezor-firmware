from trezor.messages.NEM2TransactionCommon import NEM2TransactionCommon
from trezor.messages.NEM2NamespaceRegistrationTransaction import NEM2NamespaceRegistrationTransaction

from . import layout, serialize

async def namespace_registration(
    ctx, public_key: bytes, common: NEM2TransactionCommon, namespace_registration: NEM2NamespaceRegistrationTransaction, node
):

    await layout.ask_namespace_registration(ctx, common, namespace_registration)

    return serialize.serialize_namespace_registration(common, namespace_registration)
