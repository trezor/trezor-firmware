from apps.nem.layout import *
from trezor.messages import NEMSignTx


async def ask_provision_namespace(ctx, msg: NEMSignTx):
    if msg.provision_namespace.parent:
        await require_confirm_action(ctx, 'Create namespace "' + msg.provision_namespace.namespace + '"' +
                                     'under namespace "' + msg.provision_namespace.parent + '"?')
    else:
        await require_confirm_action(ctx, 'Create namespace "' + msg.provision_namespace.namespace + '"?')
    await require_confirm_fee(ctx, 'Confirm rental fee', msg.provision_namespace.fee)

    await require_confirm_final(ctx, msg.transaction.fee)
