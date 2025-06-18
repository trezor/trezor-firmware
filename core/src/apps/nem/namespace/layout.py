from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import NEMProvisionNamespace, NEMTransactionCommon
    from trezor.ui.layouts import PropertyType


async def ask_provision_namespace(
    common: NEMTransactionCommon, namespace: NEMProvisionNamespace
) -> None:
    from trezor import TR

    from ..layout import (
        require_confirm_content,
        require_confirm_fee,
        require_confirm_final,
    )

    if namespace.parent:
        content: list[PropertyType] = [
            (TR.nem__create_namespace, namespace.namespace, False),
            (TR.nem__under_namespace, namespace.parent, False),
        ]
        await require_confirm_content(TR.nem__confirm_namespace, content)
    else:
        content = [(TR.nem__create_namespace, namespace.namespace, False)]
        await require_confirm_content(TR.nem__confirm_namespace, content)

    await require_confirm_fee(TR.nem__confirm_rental_fee, namespace.fee)

    await require_confirm_final(common.fee)
