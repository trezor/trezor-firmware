from trezor.crypto.curve import secp256k1
from trezor.crypto.hashlib import sha3_256
from trezor.messages.EthereumAddress import EthereumAddress

from apps.common import paths
from apps.common.layout import address_n_to_str, show_address, show_qr
from apps.ethereum import CURVE, networks
from apps.ethereum.address import address_from_bytes, validate_full_path
from apps.ethereum.keychain import with_keychain_from_path


@with_keychain_from_path
async def get_address(ctx, msg, keychain):
    await paths.validate_path(ctx, validate_full_path, keychain, msg.address_n, CURVE)

    node = keychain.derive(msg.address_n)
    seckey = node.private_key()
    public_key = secp256k1.publickey(seckey, False)  # uncompressed
    address_bytes = sha3_256(public_key[1:], keccak=True).digest()[12:]

    if len(msg.address_n) > 1:  # path has slip44 network identifier
        network = networks.by_slip44(msg.address_n[1] & 0x7FFFFFFF)
    else:
        network = None
    address = address_from_bytes(address_bytes, network)

    if msg.show_display:
        desc = address_n_to_str(msg.address_n)
        while True:
            if await show_address(ctx, address, desc=desc):
                break
            if await show_qr(ctx, address, desc=desc):
                break

    return EthereumAddress(address=address)
