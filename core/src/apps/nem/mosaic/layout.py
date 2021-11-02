from trezor import ui
from trezor.enums import NEMMosaicLevy, NEMSupplyChangeType
from trezor.messages import (
    NEMMosaicCreation,
    NEMMosaicDefinition,
    NEMMosaicSupplyChange,
    NEMTransactionCommon,
)
from trezor.ui.layouts import confirm_properties

from ..layout import (
    require_confirm_content,
    require_confirm_fee,
    require_confirm_final,
    require_confirm_text,
)

if False:
    from trezor.wire import Context


async def ask_mosaic_creation(
    ctx: Context, common: NEMTransactionCommon, creation: NEMMosaicCreation
) -> None:
    await require_confirm_content(ctx, "Create mosaic", _creation_message(creation))
    await require_confirm_properties(ctx, creation.definition)
    await require_confirm_fee(ctx, "Confirm creation fee", creation.fee)

    await require_confirm_final(ctx, common.fee)


async def ask_supply_change(
    ctx: Context, common: NEMTransactionCommon, change: NEMMosaicSupplyChange
) -> None:
    await require_confirm_content(ctx, "Supply change", _supply_message(change))
    if change.type == NEMSupplyChangeType.SupplyChange_Decrease:
        msg = "Decrease supply by " + str(change.delta) + " whole units?"
    elif change.type == NEMSupplyChangeType.SupplyChange_Increase:
        msg = "Increase supply by " + str(change.delta) + " whole units?"
    else:
        raise ValueError("Invalid supply change type")
    await require_confirm_text(ctx, msg)

    await require_confirm_final(ctx, common.fee)


def _creation_message(mosaic_creation: NEMMosaicCreation) -> list[tuple[str, str]]:
    return [
        ("Create mosaic", mosaic_creation.definition.mosaic),
        ("under namespace", mosaic_creation.definition.namespace),
    ]


def _supply_message(supply_change: NEMMosaicSupplyChange) -> list[tuple[str, str]]:
    return [
        ("Modify supply for", supply_change.mosaic),
        ("under namespace", supply_change.namespace),
    ]


async def require_confirm_properties(
    ctx: Context, definition: NEMMosaicDefinition
) -> None:
    properties = []

    # description
    if definition.description:
        properties.append(("Description:", definition.description))

    # transferable
    if definition.transferable:
        transferable = "Yes"
    else:
        transferable = "No"
    properties.append(("Transferable?", transferable))

    # mutable_supply
    if definition.mutable_supply:
        imm = "mutable"
    else:
        imm = "immutable"
    if definition.supply:
        properties.append(("Initial supply:", str(definition.supply) + "\n" + imm))
    else:
        properties.append(("Initial supply:", imm))

    # levy
    if definition.levy:
        assert definition.levy_address is not None
        assert definition.levy_namespace is not None
        assert definition.levy_mosaic is not None
        properties.append(("Levy recipient:", definition.levy_address))

        properties.append(("Levy fee:", str(definition.fee)))
        properties.append(("Levy divisibility:", str(definition.divisibility)))

        properties.append(("Levy namespace:", definition.levy_namespace))
        properties.append(("Levy mosaic:", definition.levy_mosaic))

        if definition.levy == NEMMosaicLevy.MosaicLevy_Absolute:
            levy_type = "absolute"
        else:
            levy_type = "percentile"
        properties.append(("Levy type:", levy_type))

    await confirm_properties(
        ctx,
        "confirm_properties",
        title="Confirm properties",
        props=properties,
        icon_color=ui.ORANGE_ICON,
    )
