from typing import TYPE_CHECKING

from apps.common.keychain import auto_keychain

if TYPE_CHECKING:
    from trezor.messages import CosmosGetPublicKey, CosmosPublicKey

    from apps.common.keychain import Keychain


@auto_keychain(__name__)
async def get_public_key(
    msg: CosmosGetPublicKey, keychain: Keychain
) -> CosmosPublicKey:
    """
    Get the Cosmos public key for the requested derivation path.

    Args:
        msg: Request containing the derivation path.
        keychain: Keychain used to derive the requested node.

    Returns:
        Cosmos secp256k1 public key in compressed form.
    """
    from trezor.messages import CosmosPublicKey

    from apps.common import paths

    address_n = msg.address_n

    await paths.validate_path(keychain, address_n)

    node = keychain.derive(address_n)
    pubkey = node.public_key()

    if msg.show_display:
        from ubinascii import b2a_base64

        from trezor.ui.layouts import show_pubkey

        await show_pubkey(b2a_base64(pubkey, newline=False).decode("ASCII"))

    return CosmosPublicKey(
        key_type="/cosmos.crypto.secp256k1.PubKey",
        value=pubkey,
    )
