from ubinascii import unhexlify

from trezor import wire

from apps.common import HARDENED, paths
from apps.polis import networks


"""
We believe Polis should use 44'/1997'/a' for everything, because it is
account-based, rather than UTXO-based. 
"""


def validate_path_for_get_public_key(path: list) -> bool:
    """
    This should be 44'/1997'/0', but other non-hardened items are allowed.
    """
    length = len(path)
    if length < 3 or length > 3:
        return False
    if path[0] != 44 | HARDENED:
        return False
    if path[1] != 1997 | HARDENED:
        return False
    return True


def validate_full_path(path: list) -> bool:
    """
    Validates derivation path to equal 44'/60'/i',
    where `i` is an address index from 0 to 1 000 000.
    """
    if len(path) > 3:
        return False
    if path[0] != 44 | HARDENED:
        return False
    if path[1] != 1997 | HARDENED:
        return False
    if path[2] > 1000000:
        return False
    return True


def address_from_bytes(address_bytes: bytes, network=None) -> str:
    """
    Converts address in bytes to a checksummed string as defined
    in https://github.com/ethereum/EIPs/blob/master/EIPS/eip-55.md
    """
    from ubinascii import hexlify
    from trezor.crypto.hashlib import sha3_256

    rskip60 = network is not None and network.rskip60

    hx = hexlify(address_bytes).decode()

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


def bytes_from_address(address: str) -> bytes:
    if len(address) == 40:
        return unhexlify(address)

    elif len(address) == 42:
        if address[0:2] not in ("0x", "0X"):
            raise wire.ProcessError("Ethereum: invalid beginning of an address")
        return unhexlify(address[2:])

    elif len(address) == 0:
        return bytes()

    raise wire.ProcessError("Ethereum: Invalid address length")
