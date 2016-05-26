#!/usr/bin/env python2
import hashlib
import os
import subprocess
import ecdsa
from binascii import hexlify, unhexlify

print 'master secret:',
h = raw_input()
if h:
    h = unhexlify(h)
else:
    h = hashlib.sha256(os.urandom(1024)).digest()

print
print 'master secret:', hexlify(h)
print

for i in range(1, 6):
    se = hashlib.sha256(h + chr(i)).hexdigest()
    print 'seckey', i, ':', se
    sk = ecdsa.SigningKey.from_secret_exponent(secexp = int(se, 16), curve=ecdsa.curves.SECP256k1, hashfunc=hashlib.sha256)
    print 'pubkey', i, ':', '04' + hexlify(sk.get_verifying_key().to_string())
    print sk.to_pem()

p = subprocess.Popen('ssss-split -t 3 -n 5 -x'.split(' '), stdin = subprocess.PIPE)
p.communicate(input = hexlify(h) + '\n')

# to recover use:
# $ ssss-combine -t 3 -x
