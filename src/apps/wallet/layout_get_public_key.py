from trezor import wire, ui
from trezor.utils import unimport


@unimport
async def layout_get_public_key(session_id, message):
    from trezor.messages.PublicKey import PublicKey
    from trezor.messages.HDNodeType import HDNodeType

    # TODO: protect with pin
    # TODO: fail if not initialized
    # TODO: derive correct node

    pubkey = PublicKey()
    pubkey.node = HDNodeType()
    pubkey.node.depth = 0
    pubkey.node.child_num = 0
    pubkey.node.fingerprint = 0
    pubkey.node.chain_code = 'deadbeef'
    pubkey.node.public_key = 'deadbeef'

    return pubkey
