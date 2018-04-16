from .helpers import LISK_CURVE, get_address_from_public_key

async def lisk_sign_message(ctx, msg):
    from trezor.messages.LiskMessageSignature import LiskMessageSignature
    from trezor.crypto.curve import ed25519
    from ..common import seed

    address_n = msg.address_n or ()
    node = await seed.derive_node(ctx, address_n, LISK_CURVE)

    seckey = node.private_key()
    public_key = ed25519.publickey(seckey)
    address = get_address_from_public_key(public_key)

    signature = ed25519.sign(seckey, msg.message)

    return LiskMessageSignature(address=address, signature=signature)
