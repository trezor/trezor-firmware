from trezor import ui
from trezor.messages import ButtonRequestType
from trezor.messages.NEM2TransactionCommon import NEM2TransactionCommon
from trezor.messages.NEM2AggregateTransaction import NEM2AggregateTransaction
from trezor.messages.NEM2InnerTransaction import NEM2InnerTransaction

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
    await confirm_inner_trasactions(ctx, aggregate.inner_transactions)
    await require_confirm_final(ctx, common.max_fee)

async def confirm_inner_trasactions(ctx, inner_transactions: NEM2InnerTransaction):
    # Starting screen
    msg = Text("Begin confirmation")
    msg.normal("Proceed to confirm {}".format(len(inner_transactions)))
    msg.normal("inner transactions?")
    await require_confirm(ctx, msg, ButtonRequestType.ConfirmOutput)

    # Make the user confirm all the properties of the aggregate transaction's
    # inner transactions.
    for transaction in inner_transactions:
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
