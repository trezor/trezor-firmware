from trezor.messages import ZcashIncomingViewingKey, ZcashGetIncomingViewingKey
from . import zip32
from trezor.crypto import zcash

if False:
    from trezor.wire import Context

async def get_ivk(ctx: Context, msg: ZcashGetIncomingViewingKey) -> ZcashIncomingViewingKey:
    zip32.verify_path(msg.z_address_n)
    master = await zip32.get_master(ctx)
    sk = master.derive(msg.z_address_n).spending_key()
    ivk = zcash.get_orchard_ivk(sk)
    return ZcashIncomingViewingKey(ivk=ivk)