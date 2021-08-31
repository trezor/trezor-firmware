from ubinascii import hexlify, unhexlify

from trezor import wire

if False:
    from .networks import NetworkInfo


def address_from_bytes(address_bytes: bytes, network: NetworkInfo | None = None) -> str:
    """
    Converts address in bytes to a checksummed string as defined
    in https://github.com/ethereum/EIPs/blob/master/EIPS/eip-55.md
    """
    from trezor.crypto.hashlib import sha3_256

    if network is not None and network.rskip60:
        prefix = str(network.chain_id) + "0x"
    else:
        prefix = ""

    address_hex = hexlify(address_bytes).decode()
    digest = sha3_256((prefix + address_hex).encode(), keccak=True).digest()

    def maybe_upper(i: int) -> str:
        """Uppercase i-th letter only if the corresponding nibble has high bit set."""
        digest_byte = digest[i // 2]
        hex_letter = address_hex[i]
        if i % 2 == 0:
            # even letter -> high nibble
            bit = 0x80
        else:
            # odd letter -> low nibble
            bit = 0x08
        if digest_byte & bit:
            return hex_letter.upper()
        else:
            return hex_letter

    return "0x" + "".join(maybe_upper(i) for i in range(len(address_hex)))


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
