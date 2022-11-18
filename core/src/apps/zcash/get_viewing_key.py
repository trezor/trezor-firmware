from typing import TYPE_CHECKING

from trezor import ui
from trezor.enums import ButtonRequestType
from trezor.messages import ZcashGetViewingKey, ZcashViewingKey
from trezor.ui.layouts import confirm_action

from apps.common import coininfo

from .orchard.keychain import with_keychain
from .unified import Typecode, encode_fvk, encode_ivk

if TYPE_CHECKING:
    from trezor.wire import Context
    from .orchard.keychain import OrchardKeychain


@with_keychain
async def get_viewing_key(
    ctx: Context, msg: ZcashGetViewingKey, keychain: OrchardKeychain
) -> ZcashViewingKey:
    await require_confirm_export_viewing_key(ctx, msg)
    coin = coininfo.by_name(msg.coin_name)
    fvk = keychain.derive(msg.z_address_n).full_viewing_key()
    if msg.full:  # Full Viewing Key
        receivers = {Typecode.ORCHARD: fvk.to_bytes()}
        key = encode_fvk(receivers, coin)
    else:  # Incoming Viewing Key
        receivers = {Typecode.ORCHARD: fvk.incoming_viewing_key()}
        key = encode_ivk(receivers, coin)
    return ZcashViewingKey(key=key)


async def require_confirm_export_viewing_key(
    ctx: Context, msg: ZcashGetViewingKey
) -> None:
    key_type = "Full" if msg.full else "Incoming"
    await confirm_action(
        ctx,
        "export_viewing_key",
        "Confirm export",
        description=f"Do you really want to export { key_type } Viewing Key?",
        icon=ui.ICON_SEND,
        icon_color=ui.GREEN,
        br_code=ButtonRequestType.SignTx,
    )
