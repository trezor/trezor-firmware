from typing import TYPE_CHECKING

from trezor.messages import NEMProvisionNamespace, NEMTransactionCommon

from . import layout, serialize

if TYPE_CHECKING:
    from trezor.wire import Context


async def namespace(
    ctx: Context,
    public_key: bytes,
    common: NEMTransactionCommon,
    namespace: NEMProvisionNamespace,
) -> bytes:
    await layout.ask_provision_namespace(ctx, common, namespace)
    return serialize.serialize_provision_namespace(common, namespace, public_key)
