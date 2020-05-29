#!/usr/bin/env python3

import json
from hashlib import blake2s
import ed25519

i18n_sk = ed25519.SigningKey(b"I18N" * 8)
# i18n_vk = i18n_sk.get_verifying_key()  # a30c461cdd0cfec95ff4a6fe09c0d47f5d2a186cbc8b51d2adeb5ce3ac3aa064

ids = json.load(open("i18n/ids.json"))
if list(range(len(ids))) != sorted(ids.values()):
    raise ValueError("IDs are not a sequence starting with zero")


class LocalizationBlock:
    def __init__(self, code):
        data = json.load(open("i18n/%s.json" % code, "rt"))
        self.code = code
        self.label = data["label"]
        del data["label"]
        if data.keys() != ids.keys():
            print(data.keys() - ids.keys(), ids.keys() - data.keys())
            raise ValueError("Keys mismatch")
        self.strings = [None] * len(data)
        for k in ids.keys():
            self.strings[ids[k]] = data[k]

    def write(self, out):

        header_bin = bytearray()
        items_bin = bytearray()
        values_bin = bytearray()
        values = {}

        for s in self.strings:
            if s is None:
                items_bin.extend(b"\x00\x00\x00\x00")  # null entry
                continue
            assert len(s) > 0
            assert len(s) < 65536
            assert len(values_bin) % 4 == 0
            if s in values:  # reuse existing value
                offset = values[s]
            else:  # add value if new
                offset = len(values_bin)
                values_bin.extend(s.encode())  # string
                if len(s) % 4 > 0:  # pad to multiple of 4
                    values_bin.extend(b"\x00" * (4 - (len(s) % 4)))
                values[s] = offset
            # add item
            items_bin.extend((offset // 4).to_bytes(2, byteorder="little"))  # offset/4
            items_bin.extend(len(s).to_bytes(2, byteorder="little"))  # length

        assert len(items_bin) == 4 * len(self.strings)
        assert 256 + len(items_bin) + len(values_bin) <= 128 * 1024
        assert len(self.code) == 5
        assert self.code[2] == "-"
        assert len(self.label) < 32

        # header section
        header_bin.extend(b"TRIB")
        header_bin.extend(len(self.strings).to_bytes(4, byteorder="little"))
        header_bin.extend(len(values_bin).to_bytes(4, byteorder="little"))
        header_bin.extend(blake2s(items_bin + values_bin).digest())
        header_bin.extend(self.code.replace("-", "").encode())
        header_bin.extend(self.label.encode().ljust(32, b"\x00"))
        header_bin.extend(b"\x00" * 112)  # reserved
        header_bin.extend(i18n_sk.sign(bytes(header_bin)))
        out.write(header_bin)
        # items section
        out.write(items_bin)
        # values section
        out.write(values_bin)


for lang in ["cs-CZ", "en-US"]:
    lb = LocalizationBlock(lang)
    lb.write(open("%s.dat" % lang, "wb"))
