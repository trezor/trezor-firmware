from typing import TYPE_CHECKING
from ubinascii import hexlify

from apps.common import seed
from apps.common.keychain import with_slip44_keychain

from . import CURVE, PATTERNS, SLIP44_ID

if TYPE_CHECKING:
    from trezor.messages import SolanaGetPublicKey, SolanaPublicKey


# TODO SOL: maybe only get_address is needed?
@with_slip44_keychain(*PATTERNS, slip44_id=SLIP44_ID, curve=CURVE)
async def get_public_key(
    msg: SolanaGetPublicKey, keychain: seed.Keychain
) -> SolanaPublicKey:
    from trezor.ui.layouts import show_pubkey
    from trezor.messages import HDNodeType, SolanaPublicKey
    from apps.common import seed

    node = keychain.derive(msg.address_n)

    node_type = HDNodeType(
        depth=node.depth(),
        child_num=node.child_num(),
        fingerprint=node.fingerprint(),
        chain_code=node.chain_code(),
        public_key=seed.remove_ed25519_prefix(node.public_key()),
    )

    if msg.show_display:
        await show_pubkey(hexlify(node.public_key).decode())

    # TODO SOL: xpub?
    return SolanaPublicKey(node=node_type, xpub=node.serialize_public(0))
