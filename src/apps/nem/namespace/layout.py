from apps.nem.layout import *
from trezor.messages import NEMSignTx


async def ask_provision_namespace(ctx, msg: NEMSignTx):
    if msg.provision_namespace.parent:
        content = [ui.NORMAL, 'Create namespace',
                   ui.BOLD, msg.provision_namespace.namespace,
                   ui.NORMAL, 'under namespace',
                   ui.BOLD, msg.provision_namespace.parent]
        await require_confirm_content(ctx, 'Confirm namespace', content)
    else:
        content = [ui.NORMAL, 'Create namespace',
                   ui.BOLD, msg.provision_namespace.namespace]
        await require_confirm_content(ctx, 'Confirm namespace', content)

    await require_confirm_fee(ctx, 'Confirm rental fee', msg.provision_namespace.fee)

    await require_confirm_final(ctx, msg.transaction.fee)
