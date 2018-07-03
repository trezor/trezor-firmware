from trezor import ui
from trezor.messages import NEMProvisionNamespace, NEMTransactionCommon

from ..layout import require_confirm_content, require_confirm_fee, require_confirm_final


async def ask_provision_namespace(
    ctx, common: NEMTransactionCommon, namespace: NEMProvisionNamespace
):
    if namespace.parent:
        content = (
            ui.NORMAL,
            "Create namespace",
            ui.BOLD,
            namespace.namespace,
            ui.NORMAL,
            "under namespace",
            ui.BOLD,
            namespace.parent,
        )
        await require_confirm_content(ctx, "Confirm namespace", content)
    else:
        content = (ui.NORMAL, "Create namespace", ui.BOLD, namespace.namespace)
        await require_confirm_content(ctx, "Confirm namespace", content)

    await require_confirm_fee(ctx, "Confirm rental fee", namespace.fee)

    await require_confirm_final(ctx, common.fee)
