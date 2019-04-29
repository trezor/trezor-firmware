#!/usr/bin/env python3
import hashlib
import os
import subprocess
from binascii import hexlify, unhexlify

import ecdsa

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
    sk = ecdsa.SigningKey.from_secret_exponent(
        secexp=int(se, 16), curve=ecdsa.curves.SECP256k1, hashfunc=hashlib.sha256
    )
    print(
        "pubkey",
        i,
        ":",
        (b"04" + hexlify(sk.get_verifying_key().to_string())).decode("ascii"),
    )
    print(sk.to_pem().decode("ascii"))

p = subprocess.Popen("ssss-split -t 3 -n 5 -x".split(" "), stdin=subprocess.PIPE)
p.communicate(input=hexlify(h) + "\n")

# to recover use:
# $ ssss-combine -t 3 -x
