from apps.common import HARDENED


"""
We believe Ethereum should use 44'/60'/a' for everything,because it is
account-based, rather than UTXO-based. Unfortunately, lot of Ethereum
tools (MEW, Metamask) do not use such scheme and set a = 0 and then
iterate the address index i. Therefore for compatibility reasons we use
the same scheme: 44'/60'/0'/0/i and only the i is being iterated.
"""


def validate_full_path(path: list) -> bool:
    """
    Validates derivation path to equal 44'/60'/0'/0/i,
    where `i` is an address index from 0 to 1 000 000.
    """
    if len(path) != 5:
        return False
    if path[0] != 44 | HARDENED:
        return False
    if path[1] != 60 | HARDENED:
        return False
    if path[2] != 0 | HARDENED:
        return False
    if path[3] != 0:
        return False
    if path[4] > 1000000:
        return False
    return True


def ethereum_address_hex(address, network=None):
    from ubinascii import hexlify
    from trezor.crypto.hashlib import sha3_256

    rskip60 = network is not None and network.rskip60

    hx = hexlify(address).decode()

    prefix = str(network.chain_id) + "0x" if rskip60 else ""
    hs = sha3_256(prefix + hx, keccak=True).digest()
    h = ""

    for i in range(20):
        l = hx[i * 2]
        if hs[i] & 0x80 and l >= "a" and l <= "f":
            l = l.upper()
        h += l
        l = hx[i * 2 + 1]
        if hs[i] & 0x08 and l >= "a" and l <= "f":
            l = l.upper()
        h += l

    return "0x" + h
