from trezor.crypto import hashlib
from trezor.crypto.curve import ed25519
from trezor.messages.TezosAddress import TezosAddress

from apps.common import seed
from apps.common.layout import show_address, show_qr
from apps.tezos.helpers import TEZOS_CURVE, b58cencode, tezos_get_address_prefix


async def get_address(ctx, msg):
    address_n = msg.address_n or ()
    node = await seed.derive_node(ctx, address_n, TEZOS_CURVE)

    sk = node.private_key()
    pk = ed25519.publickey(sk)
    pkh = hashlib.blake2b(pk, outlen=20).digest()
    address = b58cencode(pkh, prefix=tezos_get_address_prefix(0))

    if msg.show_display:
        while True:
            if await show_address(ctx, address):
                break
            if await show_qr(ctx, address):
                break

    return TezosAddress(address=address)
