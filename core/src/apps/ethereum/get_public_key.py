from trezor.messages.EthereumPublicKey import EthereumPublicKey
from trezor.messages.HDNodeType import HDNodeType

from apps.common import coins, layout, paths

from .keychain import with_keychain_from_path


@with_keychain_from_path(paths.PATTERN_BIP44_PUBKEY)
async def get_public_key(ctx, msg, keychain):
    await paths.validate_path(ctx, keychain, msg.address_n)
    node = keychain.derive(msg.address_n)

    # we use the Bitcoin format for Ethereum xpubs
    btc = coins.by_name("Bitcoin")
    node_xpub = node.serialize_public(btc.xpub_magic)

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
        await layout.show_pubkey(ctx, pubkey)

    return EthereumPublicKey(node=node_type, xpub=node_xpub)
