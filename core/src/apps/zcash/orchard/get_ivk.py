from trezor.messages import ZcashIncomingViewingKey, ZcashGetIncomingViewingKey
from .. import layout
from .keychain import with_keychain

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from trezor.wire import Context
    from .keychain import OrchardKeychain

@with_keychain
async def get_fvk(
    ctx: Context,
    msg: ZcashGetIncomingViewingKey,
    keychain: OrchardKeychain
) -> ZcashIncomingViewingKey:
    await layout.require_confirm_export_ivk(ctx)
    ivk = keychain.derive(msg.z_address_n).incoming_viewing_key()
    return ZcashIncomingViewingKey(ivk=ivk)
