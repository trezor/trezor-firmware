#!/usr/bin/env python3
import sys

from fill_t1_fw_signatures import Signatures

from trezorlib.btc import get_public_node, sign_message
from trezorlib.client import get_default_client
from trezorlib.tools import parse_path

# arg1 is input trezor.bin filename to be signed
# arg2 is output filename, if omitted, will use input file + ".signed"
client = get_default_client()
in_fw_fname = sys.argv[1]
try:
    out_fw_fname = sys.argv[2]
except IndexError:
    out_fw_fname = in_fw_fname + ".signed"

# These 3 keys will be used in this order to sign the FW
# each index can be >= 1 and <= 3
sig_indices = [1, 2]

print(f"Input trezor.bin file: {in_fw_fname}")
print(f"Output signed trezor.bin file: {out_fw_fname}")

signatures = Signatures(in_fw_fname)
digest = signatures.header_hash
assert len(digest) == 32

for i in sig_indices:
    index = i - 1  # in FW indices are indexed from 1, 0 means none
    print(f"--- Key {index}, sigindex {i}")
    path_text = f"m/44'/0'/{index}'/0/0"
    ADDRESS_N = parse_path(path_text)
    print("Addres_n", path_text, ADDRESS_N)

    node = get_public_node(client, ADDRESS_N)
    print("Public key:", node.node.public_key.hex())
    print("xpub:", node.xpub)

    signature = sign_message(client, "Bitcoin", ADDRESS_N, digest)
    sig_64bytes = signature.signature[
        1:
    ]  # first byte stripped to match normal secp256k1
    assert len(sig_64bytes) == 64
    print("Signature:", sig_64bytes.hex())
    print("=================================")

    signatures.signature_pairs.append((i, sig_64bytes))

signatures.patch_signatures()
signatures.write_output_fw(out_fw_fname)
