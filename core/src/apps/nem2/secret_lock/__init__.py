from trezor.messages.NEM2TransactionCommon import NEM2TransactionCommon
from trezor.messages.NEM2SecretLockTransaction import NEM2SecretLockTransaction
from trezor.messages.NEM2SecretProofTransaction import NEM2SecretProofTransaction

from . import layout, serialize

async def secret_lock(
    ctx, common: NEM2TransactionCommon, secret_lock: NEM2SecretLockTransaction
) -> bytearray:
    await layout.ask_secret_lock(ctx, common, secret_lock)
    return serialize.serialize_secret_lock(common, secret_lock)

async def secret_proof(
    ctx, common: NEM2TransactionCommon, secret_proof: NEM2SecretProofTransaction
) -> bytearray:
    await layout.ask_secret_proof(ctx, common, secret_proof)
    return serialize.serialize_secret_proof(common, secret_proof)
