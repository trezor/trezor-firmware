from trezor.messages.NEM2TransactionCommon import NEM2TransactionCommon
from trezor.messages.NEM2HashLockTransaction import NEM2HashLockTransaction

from . import layout, serialize

async def hash_lock(
    ctx, common: NEM2TransactionCommon, hash_lock: NEM2HashLockTransaction
) -> bytearray:
    await layout.ask_hash_lock(ctx, common, hash_lock)
    return serialize.serialize_hash_lock(common, hash_lock)
