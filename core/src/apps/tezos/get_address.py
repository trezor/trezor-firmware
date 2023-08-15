from typing import TYPE_CHECKING

from apps.common.keychain import with_slip44_keychain

from . import CURVE, PATTERNS, SLIP44_ID

if TYPE_CHECKING:
    from trezor.messages import TezosAddress, TezosGetAddress

    from apps.common.keychain import Keychain


@with_slip44_keychain(*PATTERNS, slip44_id=SLIP44_ID, curve=CURVE)
async def get_address(msg: TezosGetAddress, keychain: Keychain) -> TezosAddress:
    from trezor.crypto import hashlib
    from trezor.messages import TezosAddress
    from trezor.ui.layouts import show_address

    from apps.common import paths, seed

    from . import helpers

    await paths.validate_path(keychain, msg.address_n)

    node = keychain.derive(msg.address_n)

    pk = seed.remove_ed25519_prefix(node.public_key())
    pkh = hashlib.blake2b(pk, outlen=helpers.PUBLIC_KEY_HASH_SIZE).digest()
    address = helpers.base58_encode_check(pkh, helpers.TEZOS_ED25519_ADDRESS_PREFIX)

    if msg.show_display:
        await show_address(address, path=paths.address_n_to_str(msg.address_n))

    return TezosAddress(address=address)
