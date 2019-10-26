from trezor.messages.NEM2GetPublicKey import NEM2GetPublicKey
from trezor.messages.NEM2PublicKey import NEM2PublicKey

from apps.common.layout import show_pubkey
from apps.common.paths import validate_path
from apps.nem2 import CURVE
from apps.nem2.helpers import check_path
# from apps.nem2.validators import validate_network


async def get_public_key(ctx, msg, keychain):
    await validate_path(ctx, check_path, keychain, msg.address_n, CURVE)

    node = keychain.derive(msg.address_n, CURVE)
    pubkey = node.public_key()

    if msg.show_display:
        await show_pubkey(ctx, pubkey)

    print("GOT THE PUBKEY", pubkey)
    return NEM2PublicKey(pubkey)
