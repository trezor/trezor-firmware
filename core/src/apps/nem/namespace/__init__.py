from trezor.messages import NEMProvisionNamespace, NEMTransactionCommon

from . import layout, serialize

if False:
    from trezor.wire import Context


async def namespace(
    ctx: Context,
    public_key: bytes,
    common: NEMTransactionCommon,
    namespace: NEMProvisionNamespace,
) -> bytearray:
    await layout.ask_provision_namespace(ctx, common, namespace)
    return serialize.serialize_provision_namespace(common, namespace, public_key)
