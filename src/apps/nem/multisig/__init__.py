from .serialize import *
from .layout import *


async def ask(ctx, msg: NEMSignTx):
    await ask_multisig(ctx, msg)


def initiate(public_key, common: NEMTransactionCommon, inner_tx: bytes) -> bytes:
    return serialize_multisig(common, public_key, inner_tx)


def cosign(public_key, common: NEMTransactionCommon, inner_tx: bytes, signer: bytes) -> bytes:
    return serialize_multisig_signature(common,
                                        public_key,
                                        inner_tx,
                                        signer)


async def aggregate_modification(ctx, public_key: bytes, msg: NEMSignTx):
    await ask_aggregate_modification(ctx, msg)
    w = serialize_aggregate_modification(msg, public_key)

    for m in msg.aggregate_modification.modifications:
        serialize_cosignatory_modification(w, m.type, m.public_key)

    if msg.aggregate_modification.relative_change:
        serialize_minimum_cosignatories(w, msg.aggregate_modification.relative_change)
    return w
