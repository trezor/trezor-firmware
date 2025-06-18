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
    from trezor.ui.layouts import PropertyType


async def ask_mosaic_creation(
    common: NEMTransactionCommon, creation: NEMMosaicCreation
) -> None:
    from ..layout import require_confirm_fee

    creation_message: list[PropertyType] = [
        (TR.nem__create_mosaic, creation.definition.mosaic, False),
        (TR.nem__under_namespace, creation.definition.namespace, False),
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

    supply_message: list[PropertyType] = [
        (TR.nem__modify_supply_for, change.mosaic, False),
        (TR.nem__under_namespace, change.namespace, False),
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

    properties: list[PropertyType] = []
    append = properties.append  # local_cache_attribute

    # description
    if definition.description:
        append((TR.nem__description, definition.description, False))

    # transferable
    transferable = TR.words__yes if definition.transferable else TR.words__no
    append((TR.nem__transferable, transferable, False))

    # mutable_supply
    imm = TR.nem__mutable if definition.mutable_supply else TR.nem__immutable
    if definition.supply:
        append((TR.nem__initial_supply, str(definition.supply) + "\n" + imm, False))
    else:
        append((TR.nem__initial_supply, imm, False))

    # levy
    if definition.levy:
        # asserts below checked in nem.validators._validate_mosaic_creation
        assert definition.levy_address is not None
        assert definition.levy_namespace is not None
        assert definition.levy_mosaic is not None

        append((TR.nem__levy_recipient, definition.levy_address, True))

        append((TR.nem__levy_fee, str(definition.fee), False))
        append((TR.nem__levy_divisibility, str(definition.divisibility), False))

        append((TR.nem__levy_namespace, definition.levy_namespace, True))
        append((TR.nem__levy_mosaic, definition.levy_mosaic, False))

        levy_type = (
            TR.nem__absolute
            if definition.levy == NEMMosaicLevy.MosaicLevy_Absolute
            else TR.nem__percentile
        )
        append((TR.nem__levy_type, levy_type, False))

    await confirm_properties(
        "confirm_properties",
        TR.nem__confirm_properties,
        properties,
    )
