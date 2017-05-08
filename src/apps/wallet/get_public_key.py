from trezor.utils import unimport


@unimport
async def layout_get_public_key(session_id, msg):
    from trezor.messages.HDNodeType import HDNodeType
    from trezor.messages.PublicKey import PublicKey
    from ..common import coins
    from ..common import seed

    address_n = msg.address_n or ()
    coin_name = msg.coin_name or 'Bitcoin'

    node = await seed.get_root(session_id)
    node.derive_path(address_n)
    coin = coins.by_name(coin_name)

    node_xpub = node.serialize_public(coin.xpub_magic)
    node_type = HDNodeType(
        depth=node.depth(),
        child_num=node.child_num(),
        fingerprint=node.fingerprint(),
        chain_code=node.chain_code(),
        public_key=node.public_key())
    return PublicKey(node=node_type, xpub=node_xpub)
