from trezor import ui

from trezor.messages import ButtonRequestType
from trezor.messages.NEM2TransactionCommon import NEM2TransactionCommon
from trezor.messages.NEM2EmbeddedTransactionCommon import NEM2EmbeddedTransactionCommon
from trezor.messages.NEM2AccountAddressRestrictionTransaction import NEM2AccountAddressRestrictionTransaction
from trezor.messages.NEM2AccountMosaicRestrictionTransaction import NEM2AccountMosaicRestrictionTransaction
from trezor.messages.NEM2AccountOperationRestrictionTransaction import NEM2AccountOperationRestrictionTransaction

from trezor.ui.text import Text
from trezor.ui.scroll import Paginated

from ..helpers import (
    map_type_to_friendly_name,
    NEM2_TRANSACTION_TYPE_ACCOUNT_ADDRESS_RESTRICTION,
    NEM2_TRANSACTION_TYPE_ACCOUNT_MOSAIC_RESTRICTION,
    NEM2_TRANSACTION_TYPE_ACCOUNT_OPERATION_RESTRICTION,
    NEM2_ACCOUNT_RESTRICTION_ALLOW_INCOMING_ADDRESS,
    NEM2_ACCOUNT_RESTRICTION_ALLOW_MOSAIC,
    NEM2_ACCOUNT_RESTRICTION_ALLOW_INCOMING_TRANSACTION_TYPE,
    NEM2_ACCOUNT_RESTRICTION_ALLOW_OUTGOING_ADDRESS,
    NEM2_ACCOUNT_RESTRICTION_ALLOW_OUTGOING_TRANSACTION_TYPE,
    NEM2_ACCOUNT_RESTRICTION_BLOCK_INCOMING_ADDRESS,
    NEM2_ACCOUNT_RESTRICTION_BLOCK_MOSAIC,
    NEM2_ACCOUNT_RESTRICTION_BLOCK_INCOMING_TRANSACTION_TYPE,
    NEM2_ACCOUNT_RESTRICTION_BLOCK_OUTGOING_ADDRESS,
    NEM2_ACCOUNT_RESTRICTION_BLOCK_OUTGOING_TRANSACTION_TYPE,
)
from ..layout import require_confirm_final

from apps.common.confirm import require_confirm
from apps.common.layout import split_address

enum_to_friendly_text = {
    NEM2_ACCOUNT_RESTRICTION_ALLOW_INCOMING_ADDRESS: "Allow only incoming\ntransactions from\na given address\n",
    NEM2_ACCOUNT_RESTRICTION_ALLOW_MOSAIC: "Allow only incoming\ntransactions containing\na given mosaic identifier\n",
    NEM2_ACCOUNT_RESTRICTION_ALLOW_INCOMING_TRANSACTION_TYPE: "Allow only outgoing\ntransactions with a\ngiven transaction\ntype",
    NEM2_ACCOUNT_RESTRICTION_ALLOW_OUTGOING_ADDRESS: "Allow only outgoing\ntransactions to a\ngiven address\n",
    NEM2_ACCOUNT_RESTRICTION_ALLOW_OUTGOING_TRANSACTION_TYPE: "Allow only outgoing\ntransactions with a\ngiven transaction type\n",
    NEM2_ACCOUNT_RESTRICTION_BLOCK_INCOMING_ADDRESS: "Block incoming\ntransactions from a\ngiven address\n",
    NEM2_ACCOUNT_RESTRICTION_BLOCK_MOSAIC: "Block incoming\ntransactions containing\na given mosaic identifier\n",
    NEM2_ACCOUNT_RESTRICTION_BLOCK_INCOMING_TRANSACTION_TYPE: "Block incoming\ntransactions with a\ngiven transaction type\n",
    NEM2_ACCOUNT_RESTRICTION_BLOCK_OUTGOING_ADDRESS: "Block outgoing\ntransactions from a\ngiven address\n",
    NEM2_ACCOUNT_RESTRICTION_BLOCK_OUTGOING_TRANSACTION_TYPE: "Block outgoing\ntransactions with a\ngiven transaction type\n"
}

async def ask_account_restriction(
    ctx,
    common: NEM2TransactionCommon | NEM2EmbeddedTransactionCommon,
    account_restriction: NEM2AccountAddressRestrictionTransaction | NEM2AccountMosaicRestrictionTransaction | NEM2AccountOperationRestrictionTransaction,
    embedded=False
):
    await require_confirm_properties_account_restriction(ctx, account_restriction, common.type)
    if not embedded:
        await require_confirm_final(ctx, common.max_fee)

async def require_confirm_properties_account_restriction(
    ctx,
    account_restriction: NEM2AccountAddressRestrictionTransaction,
    entity_type: int
):
    properties = []

    # Restriction Type
    restriction_type = account_restriction.restriction_type
    if restriction_type in enum_to_friendly_text:
        friendly_text = enum_to_friendly_text[restriction_type]
        t = Text("Confirm properties", ui.ICON_SEND, new_lines=True, max_lines=10)
        t.bold("Restriction type:")
        
        # Create a new text line when \n occurs in the string
        # Used to avoid the automatic text overflow that adds hyphens mid word
        text_lines = friendly_text.split("\n")
        for i, text in enumerate(text_lines):
            if i == len(text_lines) - 1: # Only do this if its the last line of text
                t.normal('{}{}(code: {})'.format(
                    text, 
                    " " if text else "", # Only put a space before "(code)" if there is text before it
                    restriction_type))
            else:
                t.normal(text)

        properties.append(t)

    # Restriction Additions
    restriction_additions = account_restriction.restriction_additions
    if restriction_additions:
        for index, restriction_addition in enumerate(restriction_additions):
            t = Text("Confirm properties", ui.ICON_SEND, new_lines=False)
            if entity_type == NEM2_TRANSACTION_TYPE_ACCOUNT_ADDRESS_RESTRICTION:
                t.bold("Add address {}:".format(index + 1))
                t.mono(*split_address(restriction_addition.address))
            elif entity_type == NEM2_TRANSACTION_TYPE_ACCOUNT_MOSAIC_RESTRICTION:
                t.bold("Add mosaic {}:".format(index + 1))
                t.mono(restriction_addition)
            elif entity_type == NEM2_TRANSACTION_TYPE_ACCOUNT_OPERATION_RESTRICTION:
                t.bold("Add type {}:".format(index + 1))
                t.mono(map_type_to_friendly_name[restriction_addition])
            properties.append(t)

    # Restriction Deletions
    restriction_deletions = account_restriction.restriction_deletions
    if restriction_deletions:
        for index, restriction_deletion in enumerate(restriction_deletions):
            t = Text("Confirm properties", ui.ICON_SEND, new_lines=False)
            if entity_type == NEM2_TRANSACTION_TYPE_ACCOUNT_ADDRESS_RESTRICTION:
                t.bold("Delete address {}:".format(index + 1))
                t.mono(*split_address(restriction_addition.address))
            elif entity_type == NEM2_TRANSACTION_TYPE_ACCOUNT_MOSAIC_RESTRICTION:
                t.bold("Delete mosaic {}:".format(index + 1))
                t.mono(restriction_addition)
            elif entity_type == NEM2_TRANSACTION_TYPE_ACCOUNT_OPERATION_RESTRICTION:
                t.bold("Delete type {}:".format(index + 1))
                t.mono(map_type_to_friendly_name[restriction_deletion])
            properties.append(t)

    paginated = Paginated(properties)
    await require_confirm(ctx, paginated, ButtonRequestType.ConfirmOutput)
