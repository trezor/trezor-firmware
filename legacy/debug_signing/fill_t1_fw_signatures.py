#!/usr/bin/env python3

import sys
from hashlib import sha256


class Signatures:
    # offsets from T1 firmware hash
    sig_offsets = [544, 608, 672]
    sigindex_offsets = [736, 737, 738]
    signature_pairs = []  # list of tupes (int, bytes)

    def __init__(self, filename):
        """Load FW, zero out signature fiels, compute header hash"""
        self.fw_image = None  # mutable bytearray
        self.load_fw(filename)
        self.header_hash = sha256(self.get_header()).digest()
        print(f"Loaded FW image with header hash {self.header_hash_hex()}")

    def load_fw(self, filename):
        """Load FW and zero out signature fiels"""
        with open(filename, "rb") as f:
            data = f.read()
            self.fw_image = bytearray(data)
        self.zero_sig_fields()

    def zero_sig_fields(self):
        """Zero out signature fields to be able to compute header hash"""
        for i in range(3):
            sigindex_ofs = self.sigindex_offsets[i]
            sig_ofs = self.sig_offsets[i]
            self.fw_image[sigindex_ofs] = 0

            self.fw_image[sig_ofs : sig_ofs + 64] = b"\x00" * 64

    def header_hash_hex(self):
        return self.header_hash.hex()

    def get_header(self):
        """Return header with zeroed out signatures as copy"""
        return bytes(self.fw_image[:1024])

    def patch_signatures(self):
        """
        Patch signatures from signature_pairs.
        Requires filling signature_pairs beforehand.
        """
        assert len(self.signature_pairs) <= 3

        for i in range(len(self.signature_pairs)):
            sigindex_ofs = self.sigindex_offsets[i]
            sig_ofs = self.sig_offsets[i]
            (sigindex, sig) = self.signature_pairs[i]

            print(f"Patching sigindex {sigindex} at offset {sigindex_ofs}")
            assert 1 <= sigindex <= 5
            self.fw_image[sigindex_ofs] = sigindex

            print(f"Patching signature {sig.hex()} at offset {sig_ofs}")
            assert len(sig) == 64
            self.fw_image[sig_ofs : sig_ofs + 64] = sig

    def write_output_fw(self, filename):
        print(f"Writing output signed FW file {filename}")
        with open(filename, "wb") as signed_fw_file:
            signed_fw_file.write(self.fw_image)


if __name__ == "__main__":
    # arg1 - unsigned trezor.bin FW
    # arg2 - list of 3 signatures and indexes in this format (split by single space):
    # index_num signature
    # e.g.
    # 1 adec956df6282c15ee4344b4cf6edbe435ed4bb13b2b7bebb9920f3d1c4a791a446e492f3ff9b86ca43f28cfce1be97c4eefa65e505e8a936876f01833366d5d

    in_fw_fname = sys.argv[1]
    signatures_fname = sys.argv[2]

    signatures = Signatures(in_fw_fname)
    i = 0
    for line in open(signatures_fname):
        i += 1
        print(f"Parsing sig line {i} - {line}")
        idx, sig = line.rstrip().split(" ")
        idx = int(idx)
        sig = bytes.fromhex(sig)
        assert idx in range(1, 6)  # 1 <= idx <= 5
        assert len(sig) == 64
        signatures.signature_pairs.append((idx, sig))

    out_fw_name = in_fw_fname + ".signed"
    signatures.patch_signatures()
    signatures.write_output_fw(out_fw_name)
