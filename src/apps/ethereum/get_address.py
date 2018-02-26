from trezor import wire, ui


async def layout_ethereum_get_address(ctx, msg):
    from trezor.messages.EthereumAddress import EthereumAddress
    from trezor.crypto.curve import secp256k1
    from trezor.crypto.hashlib import sha3_256
    from ..common import seed

    address_n = msg.address_n or ()

    node = await seed.derive_node(ctx, address_n)

    seckey = node.private_key()
    public_key = secp256k1.publickey(seckey, False)  # uncompressed
    address = sha3_256(public_key[1:]).digest(True)[12:]  # Keccak

    if msg.show_display:
        await _show_address(ctx, address)

    return EthereumAddress(address=address)


async def _show_address(ctx, address):
    from trezor.messages.ButtonRequestType import Address
    from trezor.ui.text import Text
    from trezor.ui.qr import Qr
    from trezor.ui.container import Container
    from ..common.confirm import require_confirm

    address = _ethereum_address_hex(address)
    lines = _split_address(address)
    content = Container(
        Qr(address, (120, 135), 3),
        Text('Confirm address', ui.ICON_DEFAULT, ui.MONO, *lines))
    await require_confirm(ctx, content, code=Address)


def _split_address(address):
    from trezor.utils import chunks
    return chunks(address, 21)


def _ethereum_address_hex(address):
    from ubinascii import hexlify
    from trezor.crypto.hashlib import sha3_256

    hx = hexlify(address).decode()
    hs = sha3_256(hx).digest(True)
    h = ''

    for i in range(20):
        l = hx[i * 2]
        if hs[i] & 0x80 and l >= 'a' and l <= 'f':
            l = l.upper()
        h += l
        l = hx[i * 2 + 1]
        if hs[i] & 0x08 and l >= 'a' and l <= 'f':
            l = l.upper()
        h += l

    return '0x' + h
