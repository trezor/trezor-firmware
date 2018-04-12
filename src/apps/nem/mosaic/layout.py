from apps.nem.layout import *
from trezor.messages import NEMSignTx
from trezor.messages import NEMSupplyChangeType


async def ask_mosaic_creation(ctx, msg: NEMSignTx):
    await require_confirm_action(ctx, 'Create mosaic "' + msg.mosaic_creation.definition.mosaic + '" under  namespace "'
                                 + msg.mosaic_creation.definition.namespace + '"?')
    await require_confirm_properties(ctx, msg.mosaic_creation.definition)
    await require_confirm_fee(ctx, 'Confirm creation fee', msg.mosaic_creation.fee)

    await require_confirm_final(ctx, msg.transaction.fee)


async def ask_mosaic_supply_change(ctx, msg: NEMSignTx):
    await require_confirm_action(ctx, 'Modify supply for "' + msg.supply_change.mosaic + '" under  namespace "'
                                 + msg.supply_change.namespace + '"?')
    if msg.supply_change.type == NEMSupplyChangeType.SupplyChange_Decrease:
        ask_msg = 'Decrease supply by ' + str(msg.supply_change.delta) + ' whole units?'
    elif msg.supply_change.type == NEMSupplyChangeType.SupplyChange_Increase:
        ask_msg = 'Increase supply by ' + str(msg.supply_change.delta) + ' whole units?'
    else:
        raise ValueError('Invalid supply change type')
    await require_confirm_action(ctx, ask_msg)

    await require_confirm_final(ctx, msg.transaction.fee)
