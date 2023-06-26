from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import NEMProvisionNamespace, NEMTransactionCommon


async def namespace(
    public_key: bytes,
    common: NEMTransactionCommon,
    namespace: NEMProvisionNamespace,
) -> bytes:
    from . import layout, serialize

    await layout.ask_provision_namespace(common, namespace)
    return serialize.serialize_provision_namespace(common, namespace, public_key)
