from .layout import *
from .serialize import *


async def namespace(ctx, public_key: bytes, msg: NEMSignTx) -> bytearray:
    await ask_provision_namespace(ctx, msg)
    return serialize_provision_namespace(msg, public_key)
