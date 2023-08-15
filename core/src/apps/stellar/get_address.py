from typing import TYPE_CHECKING

from apps.common.keychain import auto_keychain

if TYPE_CHECKING:
    from trezor.messages import StellarAddress, StellarGetAddress

    from apps.common.keychain import Keychain


@auto_keychain(__name__)
async def get_address(msg: StellarGetAddress, keychain: Keychain) -> StellarAddress:
    from trezor.messages import StellarAddress
    from trezor.ui.layouts import show_address

    from apps.common import paths, seed

    from . import helpers

    await paths.validate_path(keychain, msg.address_n)

    node = keychain.derive(msg.address_n)
    pubkey = seed.remove_ed25519_prefix(node.public_key())
    address = helpers.address_from_public_key(pubkey)

    if msg.show_display:
        path = paths.address_n_to_str(msg.address_n)
        await show_address(address, case_sensitive=False, path=path)

    return StellarAddress(address=address)
