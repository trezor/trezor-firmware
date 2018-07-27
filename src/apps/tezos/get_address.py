from trezor.crypto import hashlib
from trezor.messages.TezosAddress import TezosAddress

from apps.common import seed
from apps.common.display_address import show_address, show_qr
from apps.tezos.helpers import (
    b58cencode,
    get_address_prefix,
    get_curve_module,
    get_curve_name,
)


async def tezos_get_address(ctx, msg):
    address_n = msg.address_n or ()
    curve = msg.curve or 0
    node = await seed.derive_node(ctx, address_n, get_curve_name(curve))

    sk = node.private_key()
    pk = get_curve_module(curve).publickey(sk)
    pkh = hashlib.blake2b(pk, outlen=20).digest()
    address = b58cencode(pkh, prefix=get_address_prefix(curve))

    if msg.show_display:
        while True:
            if await show_address(ctx, address):
                break
            if await show_qr(ctx, address):
                break

    return TezosAddress(address=address)
