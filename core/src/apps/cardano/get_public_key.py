from ubinascii import hexlify

from trezor import log, wire
from trezor.messages.CardanoPublicKey import CardanoPublicKey
from trezor.messages.HDNodeType import HDNodeType
from trezor.ui.layouts import require, show_pubkey

from apps.common import paths
from apps.common.seed import remove_ed25519_prefix

from . import seed
from .helpers.paths import SCHEMA_PUBKEY

if False:
    from typing import List
    from trezor.messages.CardanoGetPublicKey import CardanoGetPublicKey


@seed.with_keychain
async def get_public_key(
    ctx: wire.Context, msg: CardanoGetPublicKey, keychain: seed.Keychain
) -> CardanoPublicKey:
    await paths.validate_path(
        ctx,
        keychain,
        msg.address_n,
        # path must match the PUBKEY schema
        SCHEMA_PUBKEY.match(msg.address_n),
    )

    try:
        key = _get_public_key(keychain, msg.address_n)
    except ValueError as e:
        if __debug__:
            log.exception(__name__, e)
        raise wire.ProcessError("Deriving public key failed")

    if msg.show_display:
        await require(show_pubkey(ctx, hexlify(key.node.public_key).decode()))
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
