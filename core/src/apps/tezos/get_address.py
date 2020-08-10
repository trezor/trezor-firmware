from trezor.crypto import hashlib
from trezor.messages.TezosAddress import TezosAddress

from apps.common import paths, seed
from apps.common.keychain import with_slip44_keychain
from apps.common.layout import address_n_to_str, show_address, show_qr
from apps.tezos import CURVE, SLIP44_ID, helpers


@with_slip44_keychain(SLIP44_ID, CURVE, allow_testnet=True)
async def get_address(ctx, msg, keychain):
    await paths.validate_path(
        ctx, helpers.validate_full_path, keychain, msg.address_n, CURVE
    )

    node = keychain.derive(msg.address_n)

    pk = seed.remove_ed25519_prefix(node.public_key())
    pkh = hashlib.blake2b(pk, outlen=20).digest()
    address = helpers.base58_encode_check(
        pkh, prefix=helpers.TEZOS_ED25519_ADDRESS_PREFIX
    )

    if msg.show_display:
        desc = address_n_to_str(msg.address_n)
        while True:
            if await show_address(ctx, address, desc=desc):
                break
            if await show_qr(ctx, address, desc=desc):
                break

    return TezosAddress(address=address)
