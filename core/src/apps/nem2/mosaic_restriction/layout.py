from trezor import ui
from trezor.messages import (
    ButtonRequestType,
    NEM2TransactionCommon,
    NEM2EmbeddedTransactionCommon,
    NEM2MosaicGlobalRestrictionTransaction,
    NEM2MosaicAddressRestrictionTransaction
)

from trezor.ui.text import Text
from trezor.ui.scroll import Paginated

from ..layout import require_confirm_final, require_confirm_text

from apps.common.confirm import require_confirm
from apps.common.layout import split_address

async def ask_global_restriction(
    ctx,
    common: NEM2TransactionCommon | NEM2EmbeddedTransactionCommon,
    global_restriction: NEM2MosaicGlobalRestrictionTransaction,
    embedded=False
):

    properties = []

    # Mosaic ID
    if global_restriction.mosaic_id:
        t = Text("Confirm properties", ui.ICON_SEND, new_lines=False)
        t.bold("Mosaic Id:")
        t.br()
        t.normal(global_restriction.mosaic_id)
        properties.append(t)

    # Reference Mosaic ID
    if global_restriction.reference_mosaic_id:
        t = Text("Confirm properties", ui.ICON_SEND, new_lines=False)
        t.bold("Reference Mosaic Id:")
        t.br()
        t.normal(global_restriction.reference_mosaic_id)
        properties.append(t)

    # Restriction Key
    if global_restriction.restriction_key:
        t = Text("Confirm properties", ui.ICON_SEND, new_lines=False)
        t.bold("Restriction Key:")
        t.br()
        t.normal(global_restriction.restriction_key)
        properties.append(t)

    # Previous Restriction Value
    if global_restriction.previous_restriction_value:
        t = Text("Confirm properties", ui.ICON_SEND, new_lines=False)
        t.bold("Previous Restriction Value:")
        t.br()
        t.normal(global_restriction.previous_restriction_value)
        properties.append(t)
    
    # Previous Restriction Type
    if global_restriction.previous_restriction_type:
        t = Text("Confirm properties", ui.ICON_SEND, new_lines=False)
        t.bold("Previous Restriction Type:")
        t.br()
        t.normal(str(global_restriction.previous_restriction_type))
        properties.append(t)
    
    # New Restriction Value
    if global_restriction.new_restriction_value:
        t = Text("Confirm properties", ui.ICON_SEND, new_lines=False)
        t.bold("New Restriction Value:")
        t.br()
        t.normal(global_restriction.new_restriction_value)
        properties.append(t)

    # New Restriction Type
    if global_restriction.new_restriction_type:
        t = Text("Confirm properties", ui.ICON_SEND, new_lines=False)
        t.bold("New Restriction Type:")
        t.br()
        t.normal(str(global_restriction.new_restriction_type))
        properties.append(t)

    paginated = Paginated(properties)
    await require_confirm(ctx, paginated, ButtonRequestType.ConfirmOutput)

    if not embedded:
        await require_confirm_final(ctx, common.max_fee)


async def ask_address_restriction(
    ctx,
    common: NEM2TransactionCommon | NEM2EmbeddedTransactionCommon,
    address_restriction: NEM2MosaicAddressRestrictionTransaction,
    embedded=False
):

    properties = []

    # Mosaic ID
    if address_restriction.mosaic_id:
        t = Text("Confirm properties", ui.ICON_SEND, new_lines=False)
        t.bold("Mosaic Id:")
        t.br()
        t.normal(address_restriction.mosaic_id)
        properties.append(t)    

    # Restriction Key
    if address_restriction.restriction_key:
        t = Text("Confirm properties", ui.ICON_SEND, new_lines=False)
        t.bold("Restriction Key:")
        t.br()
        t.normal(address_restriction.restriction_key)
        properties.append(t)

    # Previous Restriction Value
    if address_restriction.previous_restriction_value:
        t = Text("Confirm properties", ui.ICON_SEND, new_lines=False)
        t.bold("Previous Restriction Value:")
        t.br()
        t.normal(address_restriction.previous_restriction_value)
        properties.append(t)
           
    # New Restriction Value
    if address_restriction.new_restriction_value:
        t = Text("Confirm properties", ui.ICON_SEND, new_lines=False)
        t.bold("New Restriction Value:")
        t.br()
        t.normal(address_restriction.new_restriction_value)
        properties.append(t)

    # Target Address
    if address_restriction.target_address:        
        t = Text("Confirm properties", ui.ICON_SEND, new_lines=False)
        t.bold("Target Address:")
        t.mono(*split_address(address_restriction.target_address.address.upper()))
        t.br()
        properties.append(t)

    paginated = Paginated(properties)
    await require_confirm(ctx, paginated, ButtonRequestType.ConfirmOutput)

    if not embedded:
        await require_confirm_final(ctx, common.max_fee)
