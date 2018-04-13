from apps.nem.layout import *
from trezor.messages import NEMSignTx
from trezor.messages import NEMSupplyChangeType
from trezor.messages import NEMMosaicDefinition
from trezor.messages import NEMMosaicLevy
from trezor.ui.scroll import Scrollpage, animate_swipe, paginate


async def ask_mosaic_creation(ctx, msg: NEMSignTx):
    await require_confirm_content(ctx, 'Create mosaic', _creation_message(msg.mosaic_creation))
    await _require_confirm_properties(ctx, msg.mosaic_creation.definition)
    await require_confirm_fee(ctx, 'Confirm creation fee', msg.mosaic_creation.fee)

    await require_confirm_final(ctx, msg.transaction.fee)


async def ask_supply_change(ctx, msg: NEMSignTx):
    await require_confirm_content(ctx, 'Supply change', _supply_message(msg.supply_change))
    if msg.supply_change.type == NEMSupplyChangeType.SupplyChange_Decrease:
        ask_msg = 'Decrease supply by ' + str(msg.supply_change.delta) + ' whole units?'
    elif msg.supply_change.type == NEMSupplyChangeType.SupplyChange_Increase:
        ask_msg = 'Increase supply by ' + str(msg.supply_change.delta) + ' whole units?'
    else:
        raise ValueError('Invalid supply change type')
    await require_confirm_text(ctx, ask_msg)

    await require_confirm_final(ctx, msg.transaction.fee)


def _creation_message(mosaic_creation):
    return [ui.NORMAL, 'Create mosaic',
            ui.BOLD, mosaic_creation.definition.mosaic,
            ui.NORMAL, 'under namespace',
            ui.BOLD, mosaic_creation.definition.namespace]


def _supply_message(supply_change):
    return [ui.NORMAL, 'Modify supply for',
            ui.BOLD, supply_change.mosaic,
            ui.NORMAL, 'under namespace',
            ui.BOLD, supply_change.namespace]


async def _require_confirm_properties(ctx, definition: NEMMosaicDefinition):
    properties = _get_mosaic_properties(definition)
    first_page = const(0)
    paginator = paginate(_show_page, len(properties), first_page, properties)
    await ctx.wait(paginator)


@ui.layout
async def _show_page(page: int, page_count: int, content):
    content = Scrollpage(content[page], page, page_count)
    if page + 1 == page_count:
        await ConfirmDialog(content)
    else:
        content.render()
        await animate_swipe()


def _get_mosaic_properties(definition: NEMMosaicDefinition):
    properties = []
    if definition.description:
        t = Text('Confirm properties', ui.ICON_SEND,
                 ui.BOLD, 'Description:',
                 ui.NORMAL, *split_words(trim(definition.description, 70), 22))
        properties.append(t)
    if definition.transferable:
        transferable = 'Yes'
    else:
        transferable = 'No'
    t = Text('Confirm properties', ui.ICON_SEND,
             ui.BOLD, 'Transferable?',
             ui.NORMAL, transferable)
    properties.append(t)
    if definition.mutable_supply:
        imm = 'mutable'
    else:
        imm = 'immutable'
    if definition.supply:
        t = Text('Confirm properties', ui.ICON_SEND,
                 ui.BOLD, 'Initial supply:',
                 ui.NORMAL, str(definition.supply),
                 ui.NORMAL, imm)
    else:
        t = Text('Confirm properties', ui.ICON_SEND,
                 ui.BOLD, 'Initial supply:',
                 ui.NORMAL, imm)
    properties.append(t)
    if definition.levy:
        t = Text('Confirm properties', ui.ICON_SEND,
                 ui.BOLD, 'Levy recipient:',
                 ui.MONO, *split_address(definition.levy_address))
        properties.append(t)
        t = Text('Confirm properties', ui.ICON_SEND,
                 ui.BOLD, 'Levy fee:',
                 ui.NORMAL, str(definition.fee),
                 ui.BOLD, 'Levy divisibility:',
                 ui.NORMAL, str(definition.divisibility))
        properties.append(t)
        t = Text('Confirm properties', ui.ICON_SEND,
                 ui.BOLD, 'Levy namespace:',
                 ui.NORMAL, definition.levy_namespace,
                 ui.BOLD, 'Levy mosaic:',
                 ui.NORMAL, definition.levy_mosaic)
        properties.append(t)
        if definition.levy == NEMMosaicLevy.MosaicLevy_Absolute:
            levy_type = 'absolute'
        else:
            levy_type = 'percentile'
        t = Text('Confirm properties', ui.ICON_SEND,
                 ui.BOLD, 'Levy type:',
                 ui.NORMAL, levy_type)
        properties.append(t)

    return properties
