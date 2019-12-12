from trezor.messages import (
    NEM2TransactionCommon,
    NEM2EmbeddedTransactionCommon,
    NEM2HashLockTransaction
)

from . import layout, serialize

async def hash_lock(
    ctx,
    common: NEM2TransactionCommon | NEM2EmbeddedTransactionCommon,
    hash_lock: NEM2HashLockTransaction
) -> bytearray:
    await layout.ask_hash_lock(ctx, common, hash_lock)
    return serialize.serialize_hash_lock(common, hash_lock)
