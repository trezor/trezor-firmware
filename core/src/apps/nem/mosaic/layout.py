from trezor import ui
from trezor.messages import (
    ButtonRequestType,
    NEMMosaicCreation,
    NEMMosaicDefinition,
    NEMMosaicLevy,
    NEMMosaicSupplyChange,
    NEMSupplyChangeType,
    NEMTransactionCommon,
)
from trezor.ui.components.tt.scroll import Paginated
from trezor.ui.components.tt.text import Text

from apps.common.layout import require_confirm, split_address

from ..layout import (
    require_confirm_content,
    require_confirm_fee,
    require_confirm_final,
    require_confirm_text,
)


async def ask_mosaic_creation(
    ctx, common: NEMTransactionCommon, creation: NEMMosaicCreation
):
    await require_confirm_content(ctx, "Create mosaic", _creation_message(creation))
    await require_confirm_properties(ctx, creation.definition)
    await require_confirm_fee(ctx, "Confirm creation fee", creation.fee)

    await require_confirm_final(ctx, common.fee)


async def ask_supply_change(
    ctx, common: NEMTransactionCommon, change: NEMMosaicSupplyChange
):
    await require_confirm_content(ctx, "Supply change", _supply_message(change))
    if change.type == NEMSupplyChangeType.SupplyChange_Decrease:
        msg = "Decrease supply by " + str(change.delta) + " whole units?"
    elif change.type == NEMSupplyChangeType.SupplyChange_Increase:
        msg = "Increase supply by " + str(change.delta) + " whole units?"
    else:
        raise ValueError("Invalid supply change type")
    await require_confirm_text(ctx, msg)

    await require_confirm_final(ctx, common.fee)


def _creation_message(mosaic_creation):
    return [
        ui.NORMAL,
        "Create mosaic",
        ui.BOLD,
        mosaic_creation.definition.mosaic,
        ui.NORMAL,
        "under namespace",
        ui.BOLD,
        mosaic_creation.definition.namespace,
    ]


def _supply_message(supply_change):
    return [
        ui.NORMAL,
        "Modify supply for",
        ui.BOLD,
        supply_change.mosaic,
        ui.NORMAL,
        "under namespace",
        ui.BOLD,
        supply_change.namespace,
    ]


async def require_confirm_properties(ctx, definition: NEMMosaicDefinition):
    properties = []

    # description
    if definition.description:
        t = Text("Confirm properties", ui.ICON_SEND, new_lines=False)
        t.bold("Description:")
        t.br()
        t.normal(*definition.description.split(" "))
        properties.append(t)

    # transferable
    if definition.transferable:
        transferable = "Yes"
    else:
        transferable = "No"
    t = Text("Confirm properties", ui.ICON_SEND)
    t.bold("Transferable?")
    t.normal(transferable)
    properties.append(t)

    # mutable_supply
    if definition.mutable_supply:
        imm = "mutable"
    else:
        imm = "immutable"
    if definition.supply:
        t = Text("Confirm properties", ui.ICON_SEND)
        t.bold("Initial supply:")
        t.normal(str(definition.supply), imm)
    else:
        t = Text("Confirm properties", ui.ICON_SEND)
        t.bold("Initial supply:")
        t.normal(imm)
    properties.append(t)

    # levy
    if definition.levy:

        t = Text("Confirm properties", ui.ICON_SEND)
        t.bold("Levy recipient:")
        t.mono(*split_address(definition.levy_address))
        properties.append(t)

        t = Text("Confirm properties", ui.ICON_SEND)
        t.bold("Levy fee:")
        t.normal(str(definition.fee))
        t.bold("Levy divisibility:")
        t.normal(str(definition.divisibility))
        properties.append(t)

        t = Text("Confirm properties", ui.ICON_SEND)
        t.bold("Levy namespace:")
        t.normal(definition.levy_namespace)
        t.bold("Levy mosaic:")
        t.normal(definition.levy_mosaic)
        properties.append(t)

        if definition.levy == NEMMosaicLevy.MosaicLevy_Absolute:
            levy_type = "absolute"
        else:
            levy_type = "percentile"
        t = Text("Confirm properties", ui.ICON_SEND)
        t.bold("Levy type:")
        t.normal(levy_type)
        properties.append(t)

    paginated = Paginated(properties)
    await require_confirm(ctx, paginated, ButtonRequestType.ConfirmOutput)
