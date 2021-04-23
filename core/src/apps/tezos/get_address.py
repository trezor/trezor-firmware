from trezor.crypto import hashlib
from trezor.messages import TezosAddress
from trezor.ui.layouts import show_address

from apps.common import paths, seed
from apps.common.keychain import with_slip44_keychain
from apps.common.layout import address_n_to_str

from . import CURVE, PATTERNS, SLIP44_ID, helpers


@with_slip44_keychain(*PATTERNS, slip44_id=SLIP44_ID, curve=CURVE)
async def get_address(ctx, msg, keychain):
    await paths.validate_path(ctx, keychain, msg.address_n)

    node = keychain.derive(msg.address_n)

    pk = seed.remove_ed25519_prefix(node.public_key())
    pkh = hashlib.blake2b(pk, outlen=helpers.PUBLIC_KEY_HASH_SIZE).digest()
    address = helpers.base58_encode_check(
        pkh, prefix=helpers.TEZOS_ED25519_ADDRESS_PREFIX
    )

    if msg.show_display:
        desc = address_n_to_str(msg.address_n)
        await show_address(ctx, address=address, address_qr=address, desc=desc)

    return TezosAddress(address=address)
