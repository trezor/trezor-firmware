from trezor import ui
from trezor.messages import (
    ButtonRequestType,
    NEM2Mosaic,
    NEM2TransactionCommon,
    NEM2EmbeddedTransactionCommon,
    NEM2MultisigModificationTransaction,
)
from trezor.ui.text import Text
from trezor.utils import format_amount
from trezor.ui.scroll import Paginated
from ubinascii import unhexlify

from ..layout import require_confirm_final, require_confirm_text

from apps.common.confirm import require_confirm
from apps.common.layout import split_address

async def ask_multisig_modification(
    ctx,
    common: NEM2TransactionCommon | NEM2EmbeddedTransactionCommon,
    multisig_modification: NEM2MultisigModificationTransaction,
    embedded=False
):


    properties = []

    # confirm approval and removal delta
    t = Text("Confirm properties", ui.ICON_SEND, new_lines=False)
    t.bold("Approval Delta:")
    t.br()
    t.normal(str(multisig_modification.min_approval_delta))
    t.br()
    t.bold("Removal Delta:")
    t.br()
    t.normal(str(multisig_modification.min_removal_delta))
    properties.append(t)

    # confirm number of additions and deletions
    t = Text("Confirm properties", ui.ICON_SEND, new_lines=False)
    t.bold("Number of Additions:")
    t.br()
    t.normal(str(len(multisig_modification.public_key_additions)))
    t.br()
    t.bold("Number of Deletions:")
    t.br()
    t.normal(str(len(multisig_modification.public_key_deletions)))
    properties.append(t)

    # confirm additions
    for addition in multisig_modification.public_key_additions:
        t = Text("Confirm properties", ui.ICON_SEND, new_lines=False)
        t.bold("Public Key Addition:")
        t.mono(*split_address(addition.upper()))

        properties.append(t)

    # confirm deletions
    for deletion in multisig_modification.public_key_deletions:
        t = Text("Confirm properties", ui.ICON_SEND, new_lines=False)
        t.bold("Public Key Deletion:")
        t.mono(*split_address(deletion.upper()))
        properties.append(t)

    paginated = Paginated(properties)
    await require_confirm(ctx, paginated, ButtonRequestType.ConfirmOutput)

    if not embedded:
        await require_confirm_final(ctx, common.max_fee)