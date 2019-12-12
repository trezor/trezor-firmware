# TODO: this is a straight copy-paste from the nem2 integration

from trezor import ui
from trezor.messages import (
    ButtonRequestType,
    NEM2TransactionCommon,
    NEM2MosaicDefinitionTransaction
)
from trezor.ui.scroll import Paginated
from trezor.ui.text import Text

from ..layout import (
    require_confirm_content,
    require_confirm_fee,
    require_confirm_final,
    require_confirm_text,
)

from ..helpers import (
    NEM2_MOSAIC_SUPPLY_CHANGE_ACTION_INCREASE,
    NEM2_MOSAIC_SUPPLY_CHANGE_ACTION_DECREASE
)

from apps.common.layout import require_confirm, split_address

async def ask_mosaic_definition(
    ctx, common: NEM2TransactionCommon, mosaic_definition: NEM2MosaicDefinitionTransaction, embedded=False
):
    await require_confirm_properties_definition(ctx, mosaic_definition)
    if not embedded:
        await require_confirm_final(ctx, common.max_fee)

async def ask_mosaic_supply(
    ctx, common: NEM2TransactionCommon, mosaic_supply: NEM2MosaicSupplyChangeTransaction, embedded=False
):
    # Initial message
    msg = Text("Supply change", ui.ICON_SEND, ui.GREEN)
    msg.normal("Modify supply for")
    msg.bold(mosaic_supply.mosaic_id)
    await require_confirm(ctx, msg, ButtonRequestType.ConfirmOutput)

    # Ask to confirm supply increase/descrease
    if mosaic_supply.action == NEM2_MOSAIC_SUPPLY_CHANGE_ACTION_DECREASE:
        msg = "Decrease supply by " + str(mosaic_supply.delta) + " whole units?"
    elif mosaic_supply.action == NEM2_MOSAIC_SUPPLY_CHANGE_ACTION_INCREASE:
        msg = "Increase supply by " + str(mosaic_supply.delta) + " whole units?"

    await require_confirm_text(ctx, msg)

    if not embedded:
        await require_confirm_final(ctx, common.max_fee)

async def require_confirm_properties_definition(ctx, mosaic_definition: NEM2MosaicDefinitionTransaction):
    properties = []
    # Mosaic ID
    if mosaic_definition.mosaic_id:
        t = Text("Confirm properties", ui.ICON_SEND, new_lines=False)
        t.bold("Mosaic Id:")
        t.br()
        t.normal(mosaic_definition.mosaic_id)
        properties.append(t)
    # Duration
    if mosaic_definition.duration:
        t = Text("Confirm properties", ui.ICON_SEND, new_lines=False)
        t.bold("Duration:")
        t.normal(str(mosaic_definition.duration))
        properties.append(t)
    # Nonce
    if mosaic_definition.nonce:
        t = Text("Confirm properties", ui.ICON_SEND, new_lines=False)
        t.bold("Nonce:")
        t.normal(str(mosaic_definition.nonce))
        properties.append(t)
    # Flags
    if mosaic_definition.flags:
        t = Text("Confirm properties", ui.ICON_SEND, new_lines=False)
        t.bold("Flags:")
        t.normal(str(mosaic_definition.flags))
        properties.append(t)
    # Divisibility
    if mosaic_definition.divisibility:
        t = Text("Confirm properties", ui.ICON_SEND, new_lines=False)
        t.bold("Divisibility:")
        t.normal(str(mosaic_definition.divisibility))
        properties.append(t)

    paginated = Paginated(properties)
    await require_confirm(ctx, paginated, ButtonRequestType.ConfirmOutput)
