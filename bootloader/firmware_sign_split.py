#!/usr/bin/env python
from __future__ import print_function
import hashlib
import os
import subprocess
import ecdsa
from binascii import hexlify, unhexlify

print('master secret:', end='')
try:
    h = raw_input()
except:
    h = input()
if h:
    h = unhexlify(h).encode('ascii')
else:
    h = hashlib.sha256(os.urandom(1024)).digest()

print()
print('master secret:', hexlify(h))
print()

for i in range(1, 6):
    se = hashlib.sha256(h + chr(i).encode('ascii')).hexdigest()
    print('seckey', i, ':', se)
    sk = ecdsa.SigningKey.from_secret_exponent(secexp = int(se, 16), curve=ecdsa.curves.SECP256k1, hashfunc=hashlib.sha256)
    print('pubkey', i, ':', (b'04' + hexlify(sk.get_verifying_key().to_string())).decode('ascii'))
    print(sk.to_pem().decode('ascii'))

p = subprocess.Popen('ssss-split -t 3 -n 5 -x'.split(' '), stdin = subprocess.PIPE)
p.communicate(input = hexlify(h) + '\n')

# to recover use:
# $ ssss-combine -t 3 -x
