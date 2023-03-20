#!/usr/bin/env python

import os
import pprint
import sys
from hashlib import sha1, sha256

import ecdsa
from fill_t1_fw_signatures import Signatures

secret_keys_hex = [
    "4444444444444444444444444444444444444444444444444444444444444444",
    "4545454545454545454545454545454545454545454545454545454545454545",
    "bfc4bca9c9c228a16639d3503d999a733a439210b64cebe757a4fd03ca46a5c8",
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
    "032c0b7cf95324a07d05398b240174dc0c2be444d96b159aa6c7f7b1e668680991",
    "02edabbd16b41c8371b92ef2f04c1185b4f03b6dcd52ba9b78d9d7c89c8f221145",
    "03665f660a5052be7a95546a02179058d93d3e08a779734914594346075bb0afd4",
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
