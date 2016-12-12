from trezor.utils import unimport


@unimport
async def layout_get_public_key(session_id, msg):
    from trezor.messages.HDNodeType import HDNodeType
    from trezor.messages.PublicKey import PublicKey
    from ..common import seed

    node = await seed.get_root(session_id)
    node.derive_path(msg.address_n or ())

    node_xpub = node.serialize_public()
    node_type = HDNodeType(
        depth=node.depth(),
        child_num=node.child_num(),
        fingerprint=node.fingerprint(),
        chain_code=node.chain_code(),
        public_key=node.public_key())
    return PublicKey(node=node_type, xpub=node_xpub)
