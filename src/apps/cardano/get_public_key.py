from ubinascii import hexlify

from trezor import log, wire
from trezor.crypto import bip32
from trezor.messages.CardanoPublicKey import CardanoPublicKey
from trezor.messages.HDNodeType import HDNodeType

from .address import _derive_hd_passphrase, derive_address_and_node

from apps.common import seed, show, storage


async def cardano_get_public_key(ctx, msg):
    mnemonic = storage.get_mnemonic()
    root_node = bip32.from_mnemonic_cardano(mnemonic)

    try:
        key = _get_public_key(root_node, msg.address_n)
    except ValueError as e:
        if __debug__:
            log.exception(__name__, e)
        raise wire.ProcessError("Deriving public key failed")
    mnemonic = None
    root_node = None

    if msg.show_display:
        await show.show_pubkey(ctx, key.node.public_key)
    return key


def _get_public_key(root_node, derivation_path: list):
    _, node = derive_address_and_node(root_node, derivation_path)

    public_key = hexlify(seed.remove_ed25519_prefix(node.public_key())).decode()
    chain_code = hexlify(node.chain_code()).decode()
    xpub_key = public_key + chain_code
    root_hd_passphrase = hexlify(_derive_hd_passphrase(root_node)).decode()

    node_type = HDNodeType(
        depth=node.depth(),
        child_num=node.child_num(),
        fingerprint=node.fingerprint(),
        chain_code=node.chain_code(),
        public_key=seed.remove_ed25519_prefix(node.public_key()),
    )

    return CardanoPublicKey(
        node=node_type, xpub=xpub_key, root_hd_passphrase=root_hd_passphrase
    )
