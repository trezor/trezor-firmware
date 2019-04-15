from ubinascii import hexlify

from trezor import log, wire
from trezor.messages.CardanoPublicKey import CardanoPublicKey
from trezor.messages.HDNodeType import HDNodeType

from apps.cardano import CURVE, seed
from apps.cardano.address import derive_address_and_node
from apps.common import layout, paths
from apps.common.seed import remove_ed25519_prefix


async def get_public_key(ctx, msg):
    keychain = await seed.get_keychain(ctx)

    await paths.validate_path(
        ctx,
        paths.validate_path_for_get_public_key,
        keychain,
        msg.address_n,
        CURVE,
        slip44_id=1815,
    )

    try:
        key = _get_public_key(keychain, msg.address_n)
    except ValueError as e:
        if __debug__:
            log.exception(__name__, e)
        raise wire.ProcessError("Deriving public key failed")

    if msg.show_display:
        await layout.show_pubkey(ctx, key.node.public_key)
    return key


def _get_public_key(keychain, derivation_path: list):
    _, node = derive_address_and_node(keychain, derivation_path)

    public_key = hexlify(remove_ed25519_prefix(node.public_key())).decode()
    chain_code = hexlify(node.chain_code()).decode()
    xpub_key = public_key + chain_code

    node_type = HDNodeType(
        depth=node.depth(),
        child_num=node.child_num(),
        fingerprint=node.fingerprint(),
        chain_code=node.chain_code(),
        public_key=remove_ed25519_prefix(node.public_key()),
    )

    return CardanoPublicKey(node=node_type, xpub=xpub_key)
