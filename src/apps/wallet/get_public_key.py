from trezor.messages.HDNodeType import HDNodeType
from trezor.messages.PublicKey import PublicKey

from apps.common import coins, seed, show


async def get_public_key(ctx, msg):
    coin_name = msg.coin_name or "Bitcoin"
    coin = coins.by_name(coin_name)

    curve_name = msg.ecdsa_curve_name
    if not curve_name:
        curve_name = coin.curve_name
    node = await seed.derive_node(ctx, msg.address_n, curve_name=curve_name)

    node_xpub = node.serialize_public(coin.xpub_magic)
    pubkey = node.public_key()
    if pubkey[0] == 1:
        pubkey = b"\x00" + pubkey[1:]
    node_type = HDNodeType(
        depth=node.depth(),
        child_num=node.child_num(),
        fingerprint=node.fingerprint(),
        chain_code=node.chain_code(),
        public_key=pubkey,
    )

    if msg.show_display:
        await show.show_pubkey(ctx, pubkey)

    return PublicKey(node=node_type, xpub=node_xpub)
