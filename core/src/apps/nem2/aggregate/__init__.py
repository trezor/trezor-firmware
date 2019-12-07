from trezor.messages.NEM2TransactionCommon import NEM2TransactionCommon
from trezor.messages.NEM2AggregateTransaction import NEM2AggregateTransaction
from .serialize import serialize_aggregate_transaction

async def aggregate(
    ctx,
    common: NEM2TransactionCommon,
    aggregate: NEM2AggregateTransaction
) -> bytearray:
    return serialize_aggregate_transaction(common, aggregate)