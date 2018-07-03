from trezor import ui
from trezor.crypto import nem
from trezor.messages import (
    ButtonRequestType,
    NEMAggregateModification,
    NEMModificationType,
    NEMSignTx,
    NEMTransactionCommon,
)
from trezor.ui.text import Text

from ..layout import (
    require_confirm,
    require_confirm_fee,
    require_confirm_final,
    require_confirm_text,
    split_address,
)


async def ask_multisig(ctx, msg: NEMSignTx):
    address = nem.compute_address(msg.multisig.signer, msg.transaction.network)
    if msg.cosigning:
        await _require_confirm_address(ctx, "Cosign transaction for", address)
    else:
        await _require_confirm_address(ctx, "Initiate transaction for", address)
    await require_confirm_fee(ctx, "Confirm multisig fee", msg.transaction.fee)


async def ask_aggregate_modification(
    ctx, common: NEMTransactionCommon, mod: NEMAggregateModification, multisig: bool
):
    if not multisig:
        await require_confirm_text(ctx, "Convert account to multisig account?")

    for m in mod.modifications:
        if m.type == NEMModificationType.CosignatoryModification_Add:
            action = "Add"
        else:
            action = "Remove"
        address = nem.compute_address(m.public_key, common.network)
        await _require_confirm_address(ctx, action + " cosignatory", address)

    if mod.relative_change:
        if multisig:
            action = "Modify the number of cosignatories by "
        else:
            action = "Set minimum cosignatories to "
        await require_confirm_text(ctx, action + str(mod.relative_change) + "?")

    await require_confirm_final(ctx, common.fee)


async def _require_confirm_address(ctx, action: str, address: str):
    text = Text("Confirm address", ui.ICON_SEND, icon_color=ui.GREEN)
    text.normal(action)
    text.mono(*split_address(address))
    await require_confirm(ctx, text, ButtonRequestType.ConfirmOutput)
