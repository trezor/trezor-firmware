from trezor.crypto.curve import nist256p1
from trezor.messages.OntologyAddress import OntologyAddress
from trezor.messages.OntologyGetAddress import OntologyGetAddress

from .helpers import CURVE, get_address_from_public_key, validate_full_path

from apps.common import paths
from apps.common.layout import show_address, show_qr


async def get_address(ctx, msg: OntologyGetAddress, keychain) -> OntologyAddress:
    await paths.validate_path(ctx, validate_full_path, keychain, msg.address_n, CURVE)

    node = keychain.derive(msg.address_n, CURVE)
    seckey = node.private_key()
    public_key = nist256p1.publickey(seckey, True)
    address = get_address_from_public_key(public_key)

    if msg.show_display:
        while True:
            if await show_address(ctx, address):
                break
            if await show_qr(ctx, address):
                break

    return OntologyAddress(address=address)
