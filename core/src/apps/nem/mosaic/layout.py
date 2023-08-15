from typing import TYPE_CHECKING

from ..layout import require_confirm_content, require_confirm_final

if TYPE_CHECKING:
    from trezor.messages import (
        NEMMosaicCreation,
        NEMMosaicDefinition,
        NEMMosaicSupplyChange,
        NEMTransactionCommon,
    )


async def ask_mosaic_creation(
    common: NEMTransactionCommon, creation: NEMMosaicCreation
) -> None:
    from ..layout import require_confirm_fee

    creation_message = [
        ("Create mosaic", creation.definition.mosaic),
        ("under namespace", creation.definition.namespace),
    ]
    await require_confirm_content("Create mosaic", creation_message)
    await _require_confirm_properties(creation.definition)
    await require_confirm_fee("Confirm creation fee", creation.fee)

    await require_confirm_final(common.fee)


async def ask_supply_change(
    common: NEMTransactionCommon, change: NEMMosaicSupplyChange
) -> None:
    from trezor.enums import NEMSupplyChangeType

    from ..layout import require_confirm_text

    supply_message = [
        ("Modify supply for", change.mosaic),
        ("under namespace", change.namespace),
    ]
    await require_confirm_content("Supply change", supply_message)
    if change.type == NEMSupplyChangeType.SupplyChange_Decrease:
        action = "Decrease"
    elif change.type == NEMSupplyChangeType.SupplyChange_Increase:
        action = "Increase"
    else:
        raise ValueError("Invalid supply change type")
    await require_confirm_text(f"{action} supply by {change.delta} whole units?")

    await require_confirm_final(common.fee)


async def _require_confirm_properties(definition: NEMMosaicDefinition) -> None:
    from trezor.enums import NEMMosaicLevy
    from trezor.ui.layouts import confirm_properties

    properties = []
    append = properties.append  # local_cache_attribute

    # description
    if definition.description:
        append(("Description:", definition.description))

    # transferable
    transferable = "Yes" if definition.transferable else "No"
    append(("Transferable?", transferable))

    # mutable_supply
    imm = "mutable" if definition.mutable_supply else "immutable"
    if definition.supply:
        append(("Initial supply:", str(definition.supply) + "\n" + imm))
    else:
        append(("Initial supply:", imm))

    # levy
    if definition.levy:
        # asserts below checked in nem.validators._validate_mosaic_creation
        assert definition.levy_address is not None
        assert definition.levy_namespace is not None
        assert definition.levy_mosaic is not None

        append(("Levy recipient:", definition.levy_address))

        append(("Levy fee:", str(definition.fee)))
        append(("Levy divisibility:", str(definition.divisibility)))

        append(("Levy namespace:", definition.levy_namespace))
        append(("Levy mosaic:", definition.levy_mosaic))

        levy_type = (
            "absolute"
            if definition.levy == NEMMosaicLevy.MosaicLevy_Absolute
            else "percentile"
        )
        append(("Levy type:", levy_type))

    await confirm_properties(
        "confirm_properties",
        "Confirm properties",
        properties,
    )
