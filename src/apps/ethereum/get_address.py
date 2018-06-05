from apps.wallet.get_address import _show_address, _show_qr


async def ethereum_get_address(ctx, msg):
    from trezor.messages.EthereumAddress import EthereumAddress
    from trezor.crypto.curve import secp256k1
    from trezor.crypto.hashlib import sha3_256
    from apps.common import seed

    address_n = msg.address_n or ()

    node = await seed.derive_node(ctx, address_n)

    seckey = node.private_key()
    public_key = secp256k1.publickey(seckey, False)  # uncompressed
    address = sha3_256(public_key[1:]).digest(True)[12:]  # Keccak

    if msg.show_display:
        hex_addr = _ethereum_address_hex(address)
        while True:
            if await _show_address(ctx, hex_addr):
                break
            if await _show_qr(ctx, hex_addr):
                break

    return EthereumAddress(address=address)


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
