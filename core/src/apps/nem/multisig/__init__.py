from trezor.messages import NEMAggregateModification, NEMSignTx, NEMTransactionCommon

from . import layout, serialize

if False:
    from trezor.wire import Context


async def ask(ctx: Context, msg: NEMSignTx) -> None:
    await layout.ask_multisig(ctx, msg)


def initiate(public_key: bytes, common: NEMTransactionCommon, inner_tx: bytes) -> bytes:
    return serialize.serialize_multisig(common, public_key, inner_tx)


def cosign(
    public_key: bytes, common: NEMTransactionCommon, inner_tx: bytes, signer: bytes
) -> bytes:
    return serialize.serialize_multisig_signature(common, public_key, inner_tx, signer)


async def aggregate_modification(
    ctx: Context,
    public_key: bytes,
    common: NEMTransactionCommon,
    aggr: NEMAggregateModification,
    is_multisig: bool,
) -> bytes:
    await layout.ask_aggregate_modification(ctx, common, aggr, is_multisig)
    w = serialize.serialize_aggregate_modification(common, aggr, public_key)

    for m in aggr.modifications:
        serialize.write_cosignatory_modification(w, m.type, m.public_key)

    if aggr.relative_change:
        serialize.write_minimum_cosignatories(w, aggr.relative_change)
    return w
