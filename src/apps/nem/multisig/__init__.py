from .serialize import *
from .layout import *
from trezor.messages.NEMAggregateModification import NEMAggregateModification


async def ask(ctx, msg: NEMSignTx):
    await ask_multisig(ctx, msg)


def initiate(public_key, common: NEMTransactionCommon, inner_tx: bytes) -> bytes:
    return serialize_multisig(common, public_key, inner_tx)


def cosign(public_key, common: NEMTransactionCommon, inner_tx: bytes, signer: bytes) -> bytes:
    return serialize_multisig_signature(common,
                                        public_key,
                                        inner_tx,
                                        signer)


async def aggregate_modification(ctx,
                                 public_key: bytes,
                                 common: NEMTransactionCommon,
                                 aggr: NEMAggregateModification,
                                 multisig: bool):
    await ask_aggregate_modification(ctx, common, aggr, multisig)
    w = serialize_aggregate_modification(common, aggr, public_key)

    for m in aggr.modifications:
        serialize_cosignatory_modification(w, m.type, m.public_key)

    if aggr.relative_change:
        serialize_minimum_cosignatories(w, aggr.relative_change)
    return w
