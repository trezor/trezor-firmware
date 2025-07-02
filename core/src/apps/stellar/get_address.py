from typing import TYPE_CHECKING

from apps.common.keychain import auto_keychain

if TYPE_CHECKING:
    from trezor.messages import StellarAddress, StellarGetAddress

    from apps.common.keychain import Keychain


@auto_keychain(__name__, slip21_namespaces=[[b"SLIP-0024"]])
async def get_address(msg: StellarGetAddress, keychain: Keychain) -> StellarAddress:
    from trezor import TR
    from trezor.messages import StellarAddress
    from trezor.ui.layouts import show_address

    from apps.common import paths, seed
    from apps.common.address_mac import get_address_mac

    from . import SLIP44_ID, helpers

    address_n = msg.address_n  # local_cache_attribute

    await paths.validate_path(keychain, address_n)

    node = keychain.derive(address_n)
    pubkey = seed.remove_ed25519_prefix(node.public_key())
    address = helpers.address_from_public_key(pubkey)
    mac = get_address_mac(address, SLIP44_ID, address_n, keychain)

    if msg.show_display:
        from . import PATTERN

        coin = "Stellar"
        await show_address(
            address,
            subtitle=TR.address__coin_address_template.format(coin),
            case_sensitive=False,
            path=paths.address_n_to_str(address_n),
            account=paths.get_account_name(coin, msg.address_n, PATTERN, SLIP44_ID),
            chunkify=bool(msg.chunkify),
        )

    return StellarAddress(address=address, mac=mac)
