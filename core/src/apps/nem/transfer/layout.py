from typing import TYPE_CHECKING

from trezor import TR
from trezor.enums import ButtonRequestType
from trezor.strings import format_amount

from ..helpers import NEM_MOSAIC_AMOUNT_DIVISOR
from ..layout import require_confirm_final
from ..mosaic.helpers import is_nem_xem_mosaic

if TYPE_CHECKING:
    from trezor.messages import (
        NEMImportanceTransfer,
        NEMMosaic,
        NEMTransactionCommon,
        NEMTransfer,
    )


async def ask_transfer(
    common: NEMTransactionCommon,
    transfer: NEMTransfer,
    encrypted: bool,
    chunkify: bool,
) -> None:
    from trezor.ui.layouts import confirm_output, confirm_text

    from ..helpers import NEM_MAX_DIVISIBILITY

    if transfer.payload:
        # require_confirm_payload
        await confirm_text(
            "confirm_payload",
            TR.nem__confirm_payload,
            bytes(transfer.payload).decode(),
            TR.nem__encrypted if encrypted else TR.nem__unencrypted,
            ButtonRequestType.ConfirmOutput,
        )

    for mosaic in transfer.mosaics:
        await _ask_transfer_mosaic(common, transfer, mosaic)

    # require_confirm_transfer
    await confirm_output(
        transfer.recipient,
        f"{format_amount(_get_xem_amount(transfer), NEM_MAX_DIVISIBILITY)} XEM",
        chunkify=chunkify,
    )

    await require_confirm_final(common.fee)


async def _ask_transfer_mosaic(
    common: NEMTransactionCommon, transfer: NEMTransfer, mosaic: NEMMosaic
) -> None:
    from trezor.enums import NEMMosaicLevy
    from trezor.ui.layouts import confirm_action, confirm_properties

    from ..helpers import NEM_LEVY_PERCENTILE_DIVISOR_ABSOLUTE
    from ..mosaic.helpers import get_mosaic_definition

    if is_nem_xem_mosaic(mosaic):
        return

    definition = get_mosaic_definition(mosaic.namespace, mosaic.mosaic, common.network)
    mosaic_quantity = mosaic.quantity * transfer.amount // NEM_MOSAIC_AMOUNT_DIVISOR

    if definition:
        await confirm_properties(
            "confirm_mosaic",
            TR.nem__confirm_mosaic,
            (
                (
                    TR.nem__confirm_transfer_of,
                    format_amount(mosaic_quantity, definition.divisibility)
                    + definition.ticker,
                ),
                (TR.nem__of, definition.name),
            ),
        )
        levy = definition.levy  # local_cache_attribute

        if levy is not None:
            if levy == NEMMosaicLevy.MosaicLevy_Absolute:
                levy_fee = levy.fee
            else:
                levy_fee = (
                    mosaic_quantity * levy.fee // NEM_LEVY_PERCENTILE_DIVISOR_ABSOLUTE
                )

            levy_msg = (
                format_amount(levy_fee, definition.divisibility) + definition.ticker
            )

            await confirm_properties(
                "confirm_mosaic_levy",
                TR.nem__confirm_mosaic,
                ((TR.nem__levy_fee_of, levy_msg),),
            )

    else:
        await confirm_action(
            "confirm_mosaic_unknown",
            TR.nem__confirm_mosaic,
            TR.nem__unknown_mosaic,
            TR.nem__divisibility_and_levy_cannot_be_shown,
            br_code=ButtonRequestType.ConfirmOutput,
        )

        await confirm_properties(
            "confirm_mosaic_transfer",
            TR.nem__confirm_mosaic,
            (
                (
                    TR.nem__confirm_transfer_of,
                    TR.nem__raw_units_template.format(mosaic_quantity),
                ),
                (TR.nem__of, f"{mosaic.namespace}.{mosaic.mosaic}"),
            ),
        )


def _get_xem_amount(transfer: NEMTransfer) -> int:
    # if mosaics are empty the transfer.amount denotes the xem amount
    if not transfer.mosaics:
        return transfer.amount
    # otherwise xem amount is taken from the nem xem mosaic if present
    for mosaic in transfer.mosaics:
        if is_nem_xem_mosaic(mosaic):
            return mosaic.quantity * transfer.amount // NEM_MOSAIC_AMOUNT_DIVISOR
    # if there are mosaics but do not include xem, 0 xem is sent
    return 0


async def ask_importance_transfer(
    common: NEMTransactionCommon, imp: NEMImportanceTransfer
) -> None:
    from trezor.enums import NEMImportanceTransferMode

    from ..layout import require_confirm_text

    if imp.mode == NEMImportanceTransferMode.ImportanceTransfer_Activate:
        m = TR.nem__activate
    else:
        m = TR.nem__deactivate
    await require_confirm_text(m + TR.nem__remote_harvesting)
    await require_confirm_final(common.fee)
