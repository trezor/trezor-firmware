from typing import TYPE_CHECKING

from trezor import TR
from trezor.crypto import nem

if TYPE_CHECKING:
    from trezor.messages import (
        NEMAggregateModification,
        NEMSignTx,
        NEMTransactionCommon,
    )


async def ask_multisig(msg: NEMSignTx) -> None:
    from ..layout import require_confirm_fee

    assert msg.multisig is not None  # sign_tx
    assert msg.multisig.signer is not None  # sign_tx
    address = nem.compute_address(msg.multisig.signer, msg.transaction.network)
    if msg.cosigning:
        await _require_confirm_address(TR.nem__cosign_transaction_for, address)
    else:
        await _require_confirm_address(TR.nem__initiate_transaction_for, address)
    await require_confirm_fee(TR.nem__confirm_multisig_fee, msg.transaction.fee)


async def ask_aggregate_modification(
    common: NEMTransactionCommon,
    mod: NEMAggregateModification,
    multisig: bool,
) -> None:
    from trezor.enums import NEMModificationType

    from ..layout import require_confirm_final, require_confirm_text

    if not multisig:
        await require_confirm_text(TR.nem__convert_account_to_multisig)

    for m in mod.modifications:
        if m.type == NEMModificationType.CosignatoryModification_Add:
            action = TR.nem__add
        else:
            action = TR.nem__remove
        address = nem.compute_address(m.public_key, common.network)
        await _require_confirm_address(action + TR.nem__cosignatory, address)

    if mod.relative_change:
        if multisig:
            action = TR.nem__modify_the_number_of_cosignatories_by
        else:
            action = TR.nem__set_minimum_cosignatories_to
        await require_confirm_text(action + str(mod.relative_change) + "?")

    await require_confirm_final(common.fee)


async def _require_confirm_address(action: str, address: str) -> None:
    from trezor.enums import ButtonRequestType
    from trezor.ui.layouts import confirm_address

    await confirm_address(
        TR.nem__confirm_address,
        address,
        description=action,
        br_name="confirm_multisig",
        br_code=ButtonRequestType.ConfirmOutput,
    )
