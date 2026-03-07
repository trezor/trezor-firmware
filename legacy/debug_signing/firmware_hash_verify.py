#!/usr/bin/env python3
import sys
from hashlib import sha256

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import Prehashed, encode_dss_signature

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

vk = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256K1(), public_key)
r = int.from_bytes(sig[:32], "big")
s = int.from_bytes(sig[32:], "big")
der_sig = encode_dss_signature(r, s)
vk.verify(der_sig, message, ec.ECDSA(Prehashed(hashes.SHA256())))
result = True
print("Signature verification result", result)
