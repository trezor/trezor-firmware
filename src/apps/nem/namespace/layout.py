from apps.nem.layout import *
from trezor.messages import NEMTransactionCommon
from trezor.messages import NEMProvisionNamespace


async def ask_provision_namespace(ctx, common: NEMTransactionCommon, namespace: NEMProvisionNamespace):
    if namespace.parent:
        content = [ui.NORMAL, 'Create namespace',
                   ui.BOLD, namespace.namespace,
                   ui.NORMAL, 'under namespace',
                   ui.BOLD, namespace.parent]
        await require_confirm_content(ctx, 'Confirm namespace', content)
    else:
        content = [ui.NORMAL, 'Create namespace',
                   ui.BOLD, namespace.namespace]
        await require_confirm_content(ctx, 'Confirm namespace', content)

    await require_confirm_fee(ctx, 'Confirm rental fee', namespace.fee)

    await require_confirm_final(ctx, common.fee)
