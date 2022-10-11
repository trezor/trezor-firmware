#!/usr/bin/env python3

import binascii
from trezorlib import _ed25519


def hex_to_c(s):
    return '"\\x' + "\\x".join([s[i : i + 2] for i in range(0, len(s), 2)]) + '"'


for c in "ABCDEFGHI":
    print()
    seckey = c.encode() * 32
    seckey_hex = binascii.hexlify(seckey).decode()
    print("seckey", seckey_hex)
    print("      ", hex_to_c(seckey_hex))
    pubkey = _ed25519.publickey_unsafe(seckey)
    pubkey_hex = binascii.hexlify(pubkey).decode()
    print("pubkey", pubkey_hex)
    print("      ", hex_to_c(pubkey_hex))
