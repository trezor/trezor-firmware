def derive_addr(pubkey: bytes, prefix: str):
    from trezor.crypto import bech32
    address_bz = derive_addr_bz(pubkey)
    converted_bits = bech32.convertbits(address_bz, 8, 5)
    return bech32.bech32_encode(prefix, converted_bits, bech32.Encoding.BECH32)

def derive_addr_bz(pubkey: bytes):
    from trezor.crypto.hashlib import sha256, ripemd160
    return ripemd160(sha256(pubkey).digest()).digest()