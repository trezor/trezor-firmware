from trezor import ui
from trezor.messages import (
    ButtonRequestType,
    NEM2TransactionCommon,
    NEM2MosaicDefinitionTransaction,
    NEM2AggregateTransaction,
    NEM2InnerTransaction
)
from trezor.ui.scroll import Paginated
from trezor.ui.text import Text

from apps.nem2.helpers import (
    NEM2_TRANSACTION_TYPE_TRANSFER,
    NEM2_TRANSACTION_TYPE_MOSAIC_DEFINITION,
    NEM2_TRANSACTION_TYPE_NAMESPACE_REGISTRATION,
    NEM2_TRANSACTION_TYPE_ADDRESS_ALIAS,
    NEM2_NAMESPACE_REGISTRATION_TYPE_ROOT,
    NEM2_TRANSACTION_TYPE_ADDRESS_ALIAS,
    NEM2_ALIAS_ACTION_TYPE_LINK,
    NEM2_ALIAS_ACTION_TYPE_UNLINK,
    captialize_string
)

from apps.nem2.transfer.layout import ask_transfer
from apps.nem2.mosaic.layout import ask_mosaic_definition
from apps.nem2.namespace.layout import ask_namespace_registration, ask_address_alias

from ..layout import (
    require_confirm_content,
    require_confirm_fee,
    require_confirm_final,
    require_confirm_text,
)

from apps.common.layout import require_confirm, split_address
from apps.common.confirm import require_confirm, require_hold_to_confirm


map_type_to_layout = {
    NEM2_TRANSACTION_TYPE_TRANSFER: ask_transfer,
    NEM2_TRANSACTION_TYPE_MOSAIC_DEFINITION: ask_mosaic_definition,
    NEM2_TRANSACTION_TYPE_NAMESPACE_REGISTRATION: ask_namespace_registration,
    NEM2_TRANSACTION_TYPE_ADDRESS_ALIAS: ask_address_alias
}

# Should be the key that maps to the transaction data
map_type_to_property = {
    NEM2_TRANSACTION_TYPE_TRANSFER: "transfer",
    NEM2_TRANSACTION_TYPE_MOSAIC_DEFINITION: "mosaic_definition",
    NEM2_TRANSACTION_TYPE_NAMESPACE_REGISTRATION: "namespace_registration",
    NEM2_TRANSACTION_TYPE_ADDRESS_ALIAS: "address_alias"
}

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
