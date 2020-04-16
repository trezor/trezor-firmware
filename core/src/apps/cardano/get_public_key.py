from ubinascii import hexlify

from trezor import log, wire
from trezor.messages.CardanoPublicKey import CardanoPublicKey
from trezor.messages.HDNodeType import HDNodeType

from apps.cardano import BYRON_PURPOSE, CURVE, SHELLEY_PURPOSE, seed
from apps.common import HARDENED, layout, paths
from apps.common.paths import is_hardened
from apps.common.seed import remove_ed25519_prefix

if False:
    from trezor.messages.CardanoGetPublicKey import CardanoGetPublicKey


@seed.with_keychains
async def get_public_key(
    ctx: wire.Context, msg: CardanoGetPublicKey, keychains: seed.Keychains
) -> CardanoPublicKey:
    await paths.validate_path(
        ctx,
        _validate_path_for_get_public_key,
        keychains,
        msg.address_n,
        CURVE,
        slip44_id=1815,
    )

    try:
        key = _get_public_key(keychains, msg.address_n)
    except ValueError as e:
        if __debug__:
            log.exception(__name__, e)
        raise wire.ProcessError("Deriving public key failed")

    if msg.show_display:
        await layout.show_pubkey(ctx, key.node.public_key)
    return key


def _get_public_key(
    keychains: seed.Keychains, derivation_path: list
) -> CardanoPublicKey:
    node = keychains.derive(derivation_path)

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


def _validate_path_for_get_public_key(path: list, slip44_id: int) -> bool:
    """
    Checks if path has at least three hardened items and slip44 id matches.
    The path is allowed to have more than three items, but all the following
    items have to be non-hardened.

    Copied from apps.common.paths and modified to also check for
    SHELLEY_PURPOSE (1852) not only BYRON_PURPOSE (44).
    """
    length = len(path)
    if length < 3 or length > 5:
        return False
    if path[0] != BYRON_PURPOSE and path[0] != SHELLEY_PURPOSE:
        return False
    if path[1] != slip44_id | HARDENED:
        return False
    if path[2] < HARDENED or path[2] > 20 | HARDENED:
        return False
    if length > 3 and is_hardened(path[3]):
        return False
    if length > 4 and is_hardened(path[4]):
        return False
    return True
