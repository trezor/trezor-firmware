from typing import TYPE_CHECKING

from trezor.messages import NEMProvisionNamespace, NEMTransactionCommon

from ..layout import require_confirm_content, require_confirm_fee, require_confirm_final

if TYPE_CHECKING:
    from trezor.wire import Context


async def ask_provision_namespace(
    ctx: Context, common: NEMTransactionCommon, namespace: NEMProvisionNamespace
) -> None:
    if namespace.parent:
        content = [
            ("Create namespace", namespace.namespace),
            ("under namespace", namespace.parent),
        ]
        await require_confirm_content(ctx, "Confirm namespace", content)
    else:
        content = [("Create namespace", namespace.namespace)]
        await require_confirm_content(ctx, "Confirm namespace", content)

    await require_confirm_fee(ctx, "Confirm rental fee", namespace.fee)

    await require_confirm_final(ctx, common.fee)
