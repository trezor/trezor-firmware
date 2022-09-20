#!/usr/bin/env python3
import sys
from hashlib import sha256

import ecdsa

# arg 1 - hex digest of firmware header with zeroed sigslots
# arg 2 - public key (compressed or uncompressed)
# arg 3 - signature 64 bytes in hex
digest = bytes.fromhex(sys.argv[1])
assert len(digest) == 32
public_key = bytes.fromhex(sys.argv[2])
sig = bytes.fromhex(sys.argv[3])
assert len(sig) == 64
# 0x18 - coin info, 0x20 - length of digest following
prefix = b"\x18Bitcoin Signed Message:\n\x20"
message_predigest = prefix + digest
message = sha256(message_predigest).digest()

vk = ecdsa.VerifyingKey.from_string(public_key, curve=ecdsa.SECP256k1, hashfunc=sha256)
result = vk.verify(sig, message)
print("Signature verification result", result)
