from typing import TYPE_CHECKING

from apps.common.keychain import auto_keychain

if TYPE_CHECKING:
    from trezor.messages import RippleAddress, RippleGetAddress

    from apps.common.keychain import Keychain


@auto_keychain(__name__)
async def get_address(msg: RippleGetAddress, keychain: Keychain) -> RippleAddress:
    # NOTE: local imports here saves 20 bytes
    from trezor.messages import RippleAddress
    from trezor.ui.layouts import show_address

    from apps.common import paths

    from .helpers import address_from_public_key

    await paths.validate_path(keychain, msg.address_n)

    node = keychain.derive(msg.address_n)
    pubkey = node.public_key()
    address = address_from_public_key(pubkey)

    if msg.show_display:
        await show_address(address, path=paths.address_n_to_str(msg.address_n))

    return RippleAddress(address=address)
