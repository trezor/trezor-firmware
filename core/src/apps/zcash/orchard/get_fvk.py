from trezor.messages import ZcashFullViewingKey, ZcashGetFullViewingKey
from .. import layout
from .keychain import with_keychain

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from trezor.wire import Context
    from .keychain import OrchardKeychain

@with_keychain
async def get_fvk(
    ctx: Context,
    msg: ZcashGetFullViewingKey,
    keychain: OrchardKeychain
) -> ZcashFullViewingKey:
    await layout.require_confirm_export_fvk(ctx)
    fvk = keychain.derive(msg.z_address_n).full_viewing_key()
    return ZcashFullViewingKey(fvk=fvk.raw(internal=msg.internal))