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

from apps.common.layout import require_confirm, split_address


async def ask_mosaic_definition(
    ctx, common: NEM2TransactionCommon, creation: NEM2MosaicDefinitionTransaction, embedded=False
):
    # await require_confirm_content(ctx, "Create mosaic", _creation_message(creation))
    # await require_confirm_properties(ctx, creation.definition)
    # await require_confirm_fee(ctx, "Confirm creation fee", creation.fee)
    if not embedded:
        await require_confirm_final(ctx, common.max_fee)

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

    paginated = Paginated(properties)
    await require_confirm(ctx, paginated, ButtonRequestType.ConfirmOutput)