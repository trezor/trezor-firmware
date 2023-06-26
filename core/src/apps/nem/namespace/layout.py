from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import NEMProvisionNamespace, NEMTransactionCommon


async def ask_provision_namespace(
    common: NEMTransactionCommon, namespace: NEMProvisionNamespace
) -> None:
    from ..layout import (
        require_confirm_content,
        require_confirm_fee,
        require_confirm_final,
    )

    if namespace.parent:
        content = [
            ("Create namespace", namespace.namespace),
            ("under namespace", namespace.parent),
        ]
        await require_confirm_content("Confirm namespace", content)
    else:
        content = [("Create namespace", namespace.namespace)]
        await require_confirm_content("Confirm namespace", content)

    await require_confirm_fee("Confirm rental fee", namespace.fee)

    await require_confirm_final(common.fee)
