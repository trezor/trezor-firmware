from .layout import *
from .serialize import *


async def namespace(ctx, public_key: bytes, common: NEMTransactionCommon, namespace: NEMProvisionNamespace) -> bytearray:
    await ask_provision_namespace(ctx, common, namespace)
    return serialize_provision_namespace(common, namespace, public_key)
