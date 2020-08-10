from ubinascii import hexlify

from trezor import log, wire
from trezor.messages.CardanoPublicKey import CardanoPublicKey
from trezor.messages.HDNodeType import HDNodeType

from apps.common import HARDENED, layout, paths
from apps.common.seed import remove_ed25519_prefix

from . import CURVE, seed
from .helpers import purposes

if False:
    from typing import List
    from trezor.messages import CardanoGetPublicKey


@seed.with_keychain
async def get_public_key(
    ctx: wire.Context, msg: CardanoGetPublicKey, keychain: seed.Keychain
):
    await paths.validate_path(
        ctx, _validate_path_for_get_public_key, keychain, msg.address_n, CURVE,
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


def _get_public_key(
    keychain: seed.Keychain, derivation_path: List[int]
) -> CardanoPublicKey:
    node = keychain.derive(derivation_path)

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


def _validate_path_for_get_public_key(path: List[int]) -> bool:
    """
    Modified version of paths.validate_path_for_get_public_key.
    Checks if path has at least three hardened items, Byron or Shelley purpose
    and slip44 id 1815. The path is allowed to have more than three items,
    but all the following items have to be non-hardened.
    """
    length = len(path)
    if length < 3 or length > 5:
        return False
    if path[0] not in (purposes.BYRON, purposes.SHELLEY):
        return False
    if path[1] != 1815 | HARDENED:
        return False
    if path[2] < HARDENED or path[2] > 20 | HARDENED:
        return False
    if length > 3 and paths.is_hardened(path[3]):
        return False
    if length > 4 and paths.is_hardened(path[4]):
        return False
    return True
