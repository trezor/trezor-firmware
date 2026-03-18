"""Get CKB address from device."""

from typing import TYPE_CHECKING

from apps.common.keychain import with_slip44_keychain

from . import CURVE, PATTERN, SLIP44_ID

if TYPE_CHECKING:
    from trezor.messages import CKBAddress, CKBGetAddress

    from apps.common.keychain import Keychain


@with_slip44_keychain(
    PATTERN, slip44_id=SLIP44_ID, curve=CURVE, slip21_namespaces=[[b"SLIP-0024"]]
)
async def get_address(msg: CKBGetAddress, keychain: Keychain) -> CKBAddress:
    # NOTE: local imports here saves bytes
    from trezor import TR
    from trezor.messages import CKBAddress
    from trezor.ui.layouts import show_address
    from trezor.wire import DataError

    from apps.common import paths
    from apps.common.address_mac import get_address_mac

    from .helpers import encode_address, get_lock_script_arg

    address_n = msg.address_n  # local_cache_attribute

    # Validate BIP-32 path
    await paths.validate_path(keychain, address_n)

    # Derive node and get public key
    node = keychain.derive(address_n)
    public_key = node.public_key()  # 33 bytes compressed

    # Derive lock script argument
    arg = get_lock_script_arg(public_key)

    # Encode to Bech32m address
    network = msg.network if msg.network else "Mainnet"

    # Validate network
    if network not in ("Mainnet", "Testnet"):
        raise DataError(f"Invalid network: {network}")

    address = encode_address(arg, network)
    mac = get_address_mac(address, SLIP44_ID, address_n, keychain)

    # Show on display if requested
    if msg.show_display:
        coin = "CKB"
        await show_address(
            address,
            subtitle=TR.address__coin_address_template.format(coin),
            path=paths.address_n_to_str(address_n),
            account=paths.get_account_name(coin, msg.address_n, PATTERN, SLIP44_ID),
            chunkify=bool(msg.chunkify),
        )

    return CKBAddress(address=address, mac=mac)
