from trezor.messages.PolisPublicKey import PolisPublicKey
from trezor.messages.HDNodeType import HDNodeType

from apps.common import coins, layout, paths
from apps.polis import CURVE, address
from apps.polis.keychain import with_keychain_from_path


@with_keychain_from_path
async def get_public_key(ctx, msg, keychain):
    await paths.validate_path(
        ctx, address.validate_full_path, keychain, msg.address_n, CURVE
    )
    node_type = HDNodeType(
        depth="x",
        child_num="x",
        fingerprint="x",
        chain_code="x",
        public_key="x",
    )

    if msg.show_display:
        await layout.show_pubkey(ctx, pubkey)

    return PolisPublicKey(node=node_type, xpub="xpub")
