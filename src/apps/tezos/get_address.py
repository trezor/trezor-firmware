from trezor.crypto import hashlib
from trezor.messages.TezosAddress import TezosAddress

from apps.common import seed
from apps.common.layout import show_address, show_qr
from apps.tezos.helpers import (
    TEZOS_CURVE,
    TEZOS_ED25519_ADDRESS_PREFIX,
    base58_encode_check,
)


async def get_address(ctx, msg):
    address_n = msg.address_n or ()
    node = await seed.derive_node(ctx, address_n, TEZOS_CURVE)

    pk = seed.remove_ed25519_prefix(node.public_key())
    pkh = hashlib.blake2b(pk, outlen=20).digest()
    address = base58_encode_check(pkh, prefix=TEZOS_ED25519_ADDRESS_PREFIX)

    if msg.show_display:
        while True:
            if await show_address(ctx, address):
                break
            if await show_qr(ctx, address):
                break

    return TezosAddress(address=address)
