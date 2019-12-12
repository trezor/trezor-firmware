from trezor import ui
from trezor.messages import ButtonRequestType
from trezor.messages.NEM2TransactionCommon import NEM2TransactionCommon
from trezor.messages.NEM2AggregateTransaction import NEM2AggregateTransaction
from trezor.messages.NEM2InnerTransaction import NEM2InnerTransaction
from trezor.messages.NEM2Cosignature import NEM2Cosignature

from trezor.ui.scroll import Paginated
from trezor.ui.text import Text

from apps.nem2.helpers import captialize_string

from ..layout import (
    require_confirm_content,
    require_confirm_fee,
    require_confirm_final,
    require_confirm_text,
)

from apps.common.layout import require_confirm, split_address
from apps.common.confirm import require_confirm, require_hold_to_confirm

from .helpers import map_type_to_property, map_type_to_layout

async def ask_aggregate(
    ctx, common: NEM2TransactionCommon, aggregate: NEM2AggregateTransaction
):
    await confirm_properties(ctx, aggregate)
    await require_confirm_final(ctx, common.max_fee)

async def confirm_properties(ctx, aggregate: NEM2AggregateTransaction):
    # Starting screen
    msg = Text("Begin confirmation")
    msg.normal("Proceed to confirm {}".format(len(aggregate.inner_transactions)))
    msg.normal("inner transactions?")
    await require_confirm(ctx, msg, ButtonRequestType.ConfirmOutput)

    # Make the user confirm all the properties of the aggregate transaction's
    # inner transactions.
    for transaction in aggregate.inner_transactions:
        tx_type = transaction.common.type
        layout_to_use = map_type_to_layout[tx_type]
        transaction_type_key = map_type_to_property[tx_type]
        # Intermediate screen between inner transactions, so the user can clearly
        # know what transaction properties they are confirming
        msg = Text("Next transaction")
        msg.normal("Proceed to confirm")
        msg.normal("the inner")
        msg.normal("{} transaction?".format(captialize_string(transaction_type_key)))
        await require_confirm(ctx, msg, ButtonRequestType.ConfirmOutput)

        await layout_to_use(
            ctx,
            transaction.common,
            transaction.__dict__[transaction_type_key],
            embedded=True)
    
    # Make the user confirm the cosignatures
    for index, cosignature in enumerate(aggregate.cosignatures):
        msg = Text("Next cosignature")
        msg.normal("Proceed to confirm")
        msg.normal("cosignature {}?".format(index + 1))
        await require_confirm(ctx, msg, ButtonRequestType.ConfirmOutput)
        await create_cosignature_confirm_page(ctx, cosignature)

async def create_cosignature_confirm_page(ctx, cosignature: NEM2Cosignature):
    properties = []
    # Public Key
    if cosignature.public_key:
        t = Text("Confirm properties", ui.ICON_SEND, new_lines=False)
        t.bold("Public Key:")
        t.mono(*split_address(cosignature.public_key))
        properties.append(t)
    # Signature
    if cosignature.signature:
        t = Text("Confirm properties", ui.ICON_SEND, new_lines=False)
        t.bold("Signature:")
        t.mono(*split_address(cosignature.signature))
        properties.append(t)

    paginated = Paginated(properties)
    await require_confirm(ctx, paginated, ButtonRequestType.ConfirmOutput)
