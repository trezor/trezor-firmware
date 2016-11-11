from trezor.utils import unimport
from ..common import seed


@unimport
async def layout_get_public_key(message, session_id):
    from trezor.messages.HDNodeType import HDNodeType
    from trezor.messages.PublicKey import PublicKey

    node = await seed.get_node(session_id, message.address_n)

    node_xpub = node.serialize_public()
    node_type = HDNodeType(
        depth=node.depth(),
        child_num=node.child_num(),
        fingerprint=node.fingerprint(),
        chain_code=node.chain_code(),
        public_key=node.public_key())
    return PublicKey(node=node_type, xpub=node_xpub)
