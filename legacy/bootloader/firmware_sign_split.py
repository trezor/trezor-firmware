#!/usr/bin/env python3
import hashlib
import os
import subprocess
from binascii import hexlify, unhexlify

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

print("master secret:", end="")
h = input()
if h:
    h = unhexlify(h).encode("ascii")
else:
    h = hashlib.sha256(os.urandom(1024)).digest()

print()
print("master secret:", hexlify(h))
print()

for i in range(1, 6):
    se = hashlib.sha256(h + chr(i).encode("ascii")).hexdigest()
    print("seckey", i, ":", se)
    sk = ec.derive_private_key(int(se, 16), ec.SECP256K1())
    pk = sk.public_key()
    pk_bytes = pk.public_bytes(
        serialization.Encoding.X962,
        serialization.PublicFormat.UncompressedPoint,
    )
    print(
        "pubkey",
        i,
        ":",
        hexlify(pk_bytes).decode("ascii"),
    )
    print(
        sk.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        ).decode("ascii")
    )

p = subprocess.Popen("ssss-split -t 3 -n 5 -x".split(" "), stdin=subprocess.PIPE)
p.communicate(input=hexlify(h) + "\n")

# to recover use:
# $ ssss-combine -t 3 -x
