from trezor.messages.SolanaAddress import SolanaAddress
from trezor.ui.layouts import show_address
from trezor.crypto import base58

from apps.common import paths
from apps.common.keychain import auto_keychain
from apps.common.layout import address_n_to_str


@auto_keychain(__name__)
async def get_address(ctx, msg, keychain):
    await paths.validate_path(ctx, keychain, msg.address_n)

    node = keychain.derive(msg.address_n)
    pubkey = node.public_key()[1:]  # skip ed25519 pubkey marker
    address = base58.encode(pubkey)

    if msg.show_display:
        desc = address_n_to_str(msg.address_n)
        await show_address(ctx, address=address, address_qr=address, desc=desc)

    return SolanaAddress(address=address)
