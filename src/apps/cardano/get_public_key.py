from ubinascii import hexlify

from trezor import log, wire
from trezor.crypto import bip32
from trezor.messages.CardanoPublicKey import CardanoPublicKey
from trezor.messages.HDNodeType import HDNodeType

from .address import derive_address_and_node

from apps.common import layout, paths, seed, storage


async def get_public_key(ctx, msg):
    await paths.validate_path(
        ctx, paths.validate_path_for_get_public_key, path=msg.address_n, slip44_id=1815
    )

    mnemonic = storage.get_mnemonic()
    passphrase = await seed._get_cached_passphrase(ctx)
    root_node = bip32.from_mnemonic_cardano(mnemonic, passphrase)

    try:
        key = _get_public_key(root_node, msg.address_n)
    except ValueError as e:
        if __debug__:
            log.exception(__name__, e)
        raise wire.ProcessError("Deriving public key failed")
    mnemonic = None
    root_node = None

    if msg.show_display:
        await layout.show_pubkey(ctx, key.node.public_key)
    return key


def _get_public_key(root_node, derivation_path: list):
    _, node = derive_address_and_node(root_node, derivation_path)

    public_key = hexlify(seed.remove_ed25519_prefix(node.public_key())).decode()
    chain_code = hexlify(node.chain_code()).decode()
    xpub_key = public_key + chain_code

    node_type = HDNodeType(
        depth=node.depth(),
        child_num=node.child_num(),
        fingerprint=node.fingerprint(),
        chain_code=node.chain_code(),
        public_key=seed.remove_ed25519_prefix(node.public_key()),
    )

    return CardanoPublicKey(node=node_type, xpub=xpub_key)
