from trezor.messages import ZcashFullViewingKey, ZcashGetFullViewingKey
from . import zip32
from trezor.crypto import zcash

if False:
    from trezor.wire import Context

async def get_fvk(ctx: Context, msg: ZcashGetFullViewingKey) -> ZcashFullViewingKey:
    zip32.verify_path(msg.z_address_n)
    master = await zip32.get_master(ctx)
    sk = master.derive(msg.z_address_n).spending_key()
    fvk = zcash.get_orchard_fvk(sk)
    return ZcashFullViewingKey(fvk=fvk)