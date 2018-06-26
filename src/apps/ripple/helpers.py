from trezor.crypto.hashlib import ripemd160, sha256

from . import base58_ripple


def address_from_public_key(pubkey: bytes):
    """Extracts public key from an address

    Ripple address is in format:
    <1-byte ripple flag> <20-bytes account id> <4-bytes dSHA-256 checksum>

    - 1-byte flag is 0x00 which is 'r' (Ripple uses its own base58 alphabet)
    - 20-bytes account id is a ripemd160(sha256(pubkey))
    - checksum is first 4 bytes of double sha256(data)

    see https://developers.ripple.com/accounts.html#address-encoding
    """
    """Returns the Ripple address created using base58"""
    h = sha256(pubkey).digest()
    h = ripemd160(h).digest()

    address = bytearray()
    address.append(0x00)  # 'r'
    address.extend(h)
    return base58_ripple.encode_check(bytes(address))
