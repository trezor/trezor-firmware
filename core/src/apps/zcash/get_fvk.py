from trezor.messages import ZcashFullViewingKey, ZcashGetFullViewingKey
from trezor.crypto import zcash
from . import zip32, layout

if False:
    from trezor.wire import Context

async def get_fvk(ctx: Context, msg: ZcashGetFullViewingKey) -> ZcashFullViewingKey:
    zip32.verify_path(msg.z_address_n)
    await layout.require_confirm_export_fvk(ctx)
    master = await zip32.get_master(ctx)
    sk = master.derive(msg.z_address_n).spending_key()
    fvk = zcash.get_orchard_fvk(sk)
    return ZcashFullViewingKey(fvk=fvk)