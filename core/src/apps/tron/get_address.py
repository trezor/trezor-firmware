from typing import TYPE_CHECKING

from apps.common.keychain import with_slip44_keychain

from . import CURVE, PATTERN, SLIP44_ID

if TYPE_CHECKING:
    from trezor.messages import TronAddress, TronGetAddress

    from apps.common.keychain import Keychain


@with_slip44_keychain(
    PATTERN, slip44_id=SLIP44_ID, curve=CURVE, slip21_namespaces=[[b"SLIP-0024"]]
)
async def get_address(msg: TronGetAddress, keychain: Keychain) -> TronAddress:
    from trezor import TR
    from trezor.crypto.curve import secp256k1
    from trezor.messages import TronAddress
    from trezor.ui.layouts import show_address

    from apps.common import paths
    from apps.common.address_mac import get_address_mac

    from . import helpers

    address_n = msg.address_n
    await paths.validate_path(keychain, address_n)
    node = keychain.derive(msg.address_n)
    public_key = secp256k1.publickey(node.private_key(), False)
    address = helpers.address_from_public_key(public_key)
    mac = get_address_mac(address, SLIP44_ID, address_n, keychain)

    if msg.show_display:
        coin = "Tron"
        await show_address(
            address,
            subtitle=TR.address__coin_address_template.format(coin),
            path=paths.address_n_to_str(address_n),
            account=paths.get_account_name(coin, msg.address_n, PATTERN, SLIP44_ID),
            chunkify=bool(msg.chunkify),
        )

    return TronAddress(address=address, mac=mac)
