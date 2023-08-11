from typing import TYPE_CHECKING

from trezor.crypto import base58

from apps.common.keychain import with_slip44_keychain

from . import CURVE, PATTERNS, SLIP44_ID

if TYPE_CHECKING:
    from trezor.messages import SolanaGetAddress, SolanaAddress

    from apps.common.keychain import Keychain


@with_slip44_keychain(*PATTERNS, slip44_id=SLIP44_ID, curve=CURVE)
async def get_address(
    msg: SolanaGetAddress,
    keychain: Keychain,
) -> SolanaAddress:
    from trezor.messages import SolanaAddress
    from trezor.ui.layouts import show_address
    from apps.common import paths, seed

    address_n = msg.address_n  # local_cache_attribute

    await paths.validate_path(keychain, address_n)

    node = keychain.derive(address_n)

    address = base58.encode(seed.remove_ed25519_prefix(node.public_key()))

    if msg.show_display:
        await show_address(address, path=paths.address_n_to_str(address_n))

    return SolanaAddress(address=address)
