#!/usr/bin/env python

import os
import pprint
import sys
from hashlib import sha1, sha256

import ecdsa
from fill_t1_fw_signatures import Signatures

secret_keys_hex = [
    "ba7994923c91771ad77c483f7d2b41f5506b82aa900e6f12edeae96c5c9f8f66",
    "81a825d359da7ec9534e6cf7dd190bdbad62e134265764a5ec3e63317b060a51",
    "37107a021e50ca3571102691606083f6a8d9cd600e35cd2c8e8f7b87796a045b",
    "5518381d95e93e8eb68a294354989906e3828f36b4556a2ad85d8333294eb1b7",
    "1d1d34168760dec092c9ff89377d8659076d2dfd95e0281719c15f90d067e211",
]

secret_keys = [
    ecdsa.SigningKey.from_string(
        bytes.fromhex(sk), curve=ecdsa.SECP256k1, hashfunc=sha256
    )
    for sk in secret_keys_hex
]
public_keys = [sk.get_verifying_key() for sk in secret_keys]
public_keys_hex = [pk.to_string("compressed").hex() for pk in public_keys]

# arg1 is input trezor.bin filename to be signed
# arg2 is output filename, if omitted, will use input file + ".signed"
in_fw_fname = sys.argv[1]
try:
    out_fw_fname = sys.argv[2]
except IndexError:
    out_fw_fname = in_fw_fname + ".signed"

# These 3 keys will be used in this order to sign the FW
# each index can be >= 1 and <= 5
sig_indices = [1, 2, 3]

print(f"Input trezor.bin file: {in_fw_fname}")
print(f"Output signed trezor.bin file: {out_fw_fname}")

# print("Public keys compressed:")
# pprint.pprint(public_keys_hex)

# Should be these public keys
assert public_keys_hex == [
    "0391cdaf3cac08c2712ee1e88cd6d346eb2c798fdaf95c0eb6efeea0d7014dac87",
    "02186ff4e2b08bc5ae0e21a508f1ced48ff451eab7d794deb0b7cbe8efd729aba7",
    "0324009f0b398ca1c335fb17a1021c3f7fb0831ddb28348a4f058b149ea4c589a0",
    "0366635d999417b65566866c65630d977a7ae723fe5f6c4cd17fa00f088ba184c1",
    "03f36c7d0fb615ada43d7188580f15ebda22d6f6b9b1a92bff16c6937799dcbc66",
]

print("Sanity check")
for (sk, pk_hex) in zip(secret_keys, public_keys_hex):
    pk = ecdsa.VerifyingKey.from_string(
        bytes.fromhex(pk_hex), curve=ecdsa.SECP256k1, hashfunc=sha256
    )
    message = bytes(os.urandom(64))

    # These should work
    sig = sk.sign_deterministic(message, hashfunc=sha256)
    pk.verify(sig, message, hashfunc=sha256)  # throws exception if wrong

    # These should fail
    try:
        sig = sk.sign_deterministic(message, hashfunc=sha1)
        pk.verify(sig, message, hashfunc=sha256)  # should throw
        raise RuntimeError("These should not have matched!")
    except ecdsa.keys.BadSignatureError:
        # print("Bad sig check fail test ok")
        pass  # fine, should have failed

print("Sanity check successful")

signatures = Signatures(in_fw_fname)
digest = signatures.header_hash
header = signatures.get_header()
assert len(digest) == 32
assert sha256(header).digest() == digest

print("Full header hex")
pprint.pprint(header.hex())

for i in sig_indices:
    index = i - 1  # in FW indices are indexed from 1, 0 means none
    print(f"--- Key {index}, sigindex {i}")
    sk = secret_keys[index]
    sig_64bytes = sk.sign_deterministic(header, hashfunc=sha256)
    assert len(sig_64bytes) == 64
    print("Signature:", sig_64bytes.hex())
    pk = ecdsa.VerifyingKey.from_string(
        bytes.fromhex(public_keys_hex[index]), curve=ecdsa.SECP256k1, hashfunc=sha256
    )
    pk.verify(sig_64bytes, header, hashfunc=sha256)  # throws exception if wrong
    print(f"Public key {public_keys_hex[index]}")
    print("Verified created sig with public key")
    print("=================================")

    signatures.signature_pairs.append((i, sig_64bytes))

signatures.patch_signatures()
signatures.write_output_fw(out_fw_fname)
