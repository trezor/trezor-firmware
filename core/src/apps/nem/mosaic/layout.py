from typing import TYPE_CHECKING

from trezor import TR

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
        (TR.nem__create_mosaic, creation.definition.mosaic),
        (TR.nem__under_namespace, creation.definition.namespace),
    ]
    await require_confirm_content(TR.nem__create_mosaic, creation_message)
    await _require_confirm_properties(creation.definition)
    await require_confirm_fee(TR.nem__confirm_creation_fee, creation.fee)

    await require_confirm_final(common.fee)


async def ask_supply_change(
    common: NEMTransactionCommon, change: NEMMosaicSupplyChange
) -> None:
    from trezor.enums import NEMSupplyChangeType

    from ..layout import require_confirm_text

    supply_message = [
        (TR.nem__modify_supply_for, change.mosaic),
        (TR.nem__under_namespace, change.namespace),
    ]
    await require_confirm_content(TR.nem__supply_change, supply_message)
    if change.type == NEMSupplyChangeType.SupplyChange_Decrease:
        action = TR.nem__decrease
    elif change.type == NEMSupplyChangeType.SupplyChange_Increase:
        action = TR.nem__increase
    else:
        raise ValueError("Invalid supply change type")
    await require_confirm_text(
        TR.nem__supply_units_template.format(action, change.delta)
    )

    await require_confirm_final(common.fee)


async def _require_confirm_properties(definition: NEMMosaicDefinition) -> None:
    from trezor.enums import NEMMosaicLevy
    from trezor.ui.layouts import confirm_properties

    properties = []
    append = properties.append  # local_cache_attribute

    # description
    if definition.description:
        append((TR.nem__description, definition.description))

    # transferable
    transferable = TR.words__yes if definition.transferable else TR.words__no
    append((TR.nem__transferable, transferable))

    # mutable_supply
    imm = TR.nem__mutable if definition.mutable_supply else TR.nem__immutable
    if definition.supply:
        append((TR.nem__initial_supply, str(definition.supply) + "\n" + imm))
    else:
        append((TR.nem__initial_supply, imm))

    # levy
    if definition.levy:
        # asserts below checked in nem.validators._validate_mosaic_creation
        assert definition.levy_address is not None
        assert definition.levy_namespace is not None
        assert definition.levy_mosaic is not None

        append((TR.nem__levy_recipient, definition.levy_address))

        append((TR.nem__levy_fee, str(definition.fee)))
        append((TR.nem__levy_divisibility, str(definition.divisibility)))

        append((TR.nem__levy_namespace, definition.levy_namespace))
        append((TR.nem__levy_mosaic, definition.levy_mosaic))

        levy_type = (
            TR.nem__absolute
            if definition.levy == NEMMosaicLevy.MosaicLevy_Absolute
            else TR.nem__percentile
        )
        append((TR.nem__levy_type, levy_type))

    await confirm_properties(
        "confirm_properties",
        TR.nem__confirm_properties,
        properties,
    )
