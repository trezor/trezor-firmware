from trezor import ui
from trezor.messages import (
    ButtonRequestType,
    NEM2TransactionCommon,
    NEM2EmbeddedTransactionCommon,
    NEM2Mosaic
)
from trezor.ui.text import Text
from trezor.ui.scroll import Paginated

from ..layout import require_confirm_final

from apps.common.confirm import require_confirm

async def ask_hash_lock(
    ctx,
    common: NEM2TransactionCommon | NEM2EmbeddedTransactionCommon,
    hash_lock: NEM2HashLockTransaction,
    embedded=False
):
    await require_confirm_properties(ctx, hash_lock)
    await require_confirm_final(ctx, common.max_fee)

async def require_confirm_properties(ctx, hash_lock: NEM2HashLockTransaction):
    properties = []
    print('drawing layout', hash_lock.mosaic, hash_lock.duration)
    # Mosaic
    if hash_lock.mosaic:
        t = Text("Confirm properties", ui.ICON_SEND, new_lines=False)
        t.bold("Mosaic Id:")
        t.normal(hash_lock.mosaic.id)
        t.br()
        t.bold("Amount:")
        t.normal(hash_lock.mosaic.amount)
        properties.append(t)
    # Duration
    if hash_lock.duration:
        t = Text("Confirm properties", ui.ICON_SEND, new_lines=False)
        t.bold("Duration:")
        t.normal(str(hash_lock.duration))
        properties.append(t)
    # Hash
    if hash_lock.hash:
        t = Text("Confirm properties", ui.ICON_SEND, new_lines=False)
        t.bold("Hash:")
        t.normal(hash_lock.hash)
        properties.append(t)

    paginated = Paginated(properties)
    await require_confirm(ctx, paginated, ButtonRequestType.ConfirmOutput)
