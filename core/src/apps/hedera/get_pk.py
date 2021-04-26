from trezor.messages.HederaGetPublicKey import HederaGetPublicKey
from trezor.messages.HederaPublicKey import HederaPublicKey
from trezor.ui.layouts import show_address

from apps.common import paths, seed
from apps.common.keychain import auto_keychain
from apps.common.layout import address_n_to_str


@auto_keychain(__name__)
async def get_pk(ctx, msg: HederaGetPublicKey, keychain):
    await paths.validate_path(ctx, keychain, msg.address_n)

    node = keychain.derive(msg.address_n)
    pubkey = seed.remove_ed25519_prefix(node.public_key())
    address = pubkey.hex()

    if msg.show_display:
        desc = address_n_to_str(msg.address_n)
        await show_address(ctx, address=address, address_qr=address.upper(), desc=desc)

    return HederaPublicKey(publicKey=pubkey)
