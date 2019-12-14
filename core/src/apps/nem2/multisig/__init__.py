from trezor.messages.NEM2TransactionCommon import NEM2TransactionCommon
from trezor.messages.NEM2MultisigModificationTransaction import NEM2MultisigModificationTransaction

from . import layout, serialize

async def multisig_modification(
    ctx,
    common: NEM2TransactionCommon,
    multisig_modification: NEM2MultisigModificationTransaction
):

    await layout.ask_multisig_modification(ctx, common, multisig_modification)

    return serialize.serialize_multisig_modification(common, multisig_modification)

