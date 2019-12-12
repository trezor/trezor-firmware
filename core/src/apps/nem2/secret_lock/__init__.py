from trezor.messages.NEM2TransactionCommon import NEM2TransactionCommon
from trezor.messages.NEM2SecretLockTransaction import NEM2SecretLockTransaction

from . import layout, serialize

async def secret_lock(
    ctx, common: NEM2TransactionCommon, secret_lock: NEM2SecretLockTransaction
) -> bytearray:
    await layout.ask_secret_lock(ctx, common, secret_lock)
    return serialize.serialize_secret_lock(common, secret_lock)
