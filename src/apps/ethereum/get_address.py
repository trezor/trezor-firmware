from .address import ethereum_address_hex, validate_full_path

from apps.common import paths
from apps.common.layout import address_n_to_str, show_address, show_qr
from apps.ethereum import networks


async def get_address(ctx, msg):
    from trezor.messages.EthereumAddress import EthereumAddress
    from trezor.crypto.curve import secp256k1
    from trezor.crypto.hashlib import sha3_256
    from apps.common import seed

    await paths.validate_path(ctx, validate_full_path, path=msg.address_n)

    node = await seed.derive_node(ctx, msg.address_n)

    seckey = node.private_key()
    public_key = secp256k1.publickey(seckey, False)  # uncompressed
    address = sha3_256(public_key[1:], keccak=True).digest()[12:]

    if msg.show_display:
        if len(msg.address_n) > 1:  # path has slip44 network identifier
            network = networks.by_slip44(msg.address_n[1] & 0x7FFFFFFF)
        else:
            network = None
        hex_addr = ethereum_address_hex(address, network)
        desc = address_n_to_str(msg.address_n)
        while True:
            if await show_address(ctx, hex_addr, desc=desc):
                break
            if await show_qr(ctx, hex_addr, desc=desc):
                break

    return EthereumAddress(address=address)
