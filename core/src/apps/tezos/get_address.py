from typing import TYPE_CHECKING

from apps.common.keychain import with_slip44_keychain

from . import CURVE, PATTERNS, SLIP44_ID

if TYPE_CHECKING:
    from trezor.messages import TezosAddress, TezosGetAddress

    from apps.common.keychain import Keychain


@with_slip44_keychain(
    *PATTERNS, slip44_id=SLIP44_ID, curve=CURVE, slip21_namespaces=[[b"SLIP-0024"]]
)
async def get_address(msg: TezosGetAddress, keychain: Keychain) -> TezosAddress:
    from trezor import TR
    from trezor.crypto import hashlib
    from trezor.messages import TezosAddress
    from trezor.ui.layouts import show_address

    from apps.common import paths, seed
    from apps.common.address_mac import get_address_mac

    from . import SLIP44_ID, helpers

    address_n = msg.address_n  # local_cache_attribute

    await paths.validate_path(keychain, address_n)

    node = keychain.derive(address_n)

    pk = seed.remove_ed25519_prefix(node.public_key())
    pkh = hashlib.blake2b(pk, outlen=helpers.PUBLIC_KEY_HASH_SIZE).digest()
    address = helpers.base58_encode_check(pkh, helpers.TEZOS_ED25519_ADDRESS_PREFIX)
    mac = get_address_mac(address, SLIP44_ID, address_n, keychain)

    if msg.show_display:
        from . import PATTERNS

        coin = "XTZ"
        await show_address(
            address,
            subtitle=TR.address__coin_address_template.format(coin),
            path=paths.address_n_to_str(address_n),
            account=paths.get_account_name(coin, address_n, PATTERNS, SLIP44_ID),
            chunkify=bool(msg.chunkify),
        )

    return TezosAddress(address=address, mac=mac)
