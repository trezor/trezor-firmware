# flake8: noqa: F403,F405
from common import *  # isort:skip

from apps.bitcoin.scripts_namecoin import (
    output_script_name_firstupdate,
    output_script_name_new,
    output_script_name_update,
)

# A canonical P2PKH inner script: OP_DUP OP_HASH160 <push20 pkh> OP_EQUALVERIFY OP_CHECKSIG.
INNER_P2PKH = unhexlify("76a914" + "00" * 20 + "88ac")

# A canonical P2SH inner script: OP_HASH160 <push20 sh> OP_EQUAL.
INNER_P2SH = unhexlify("a914" + "11" * 20 + "87")


class TestScriptsNamecoin(unittest.TestCase):
    def test_name_new_p2pkh(self):
        commitment = b"\x01" * 20
        script = output_script_name_new(commitment, INNER_P2PKH)
        # OP_1 (0x51) + push20 (0x14) + 20 bytes + OP_2DROP (0x6d) + inner
        expected = (
            b"\x51" + b"\x14" + commitment + b"\x6d" + INNER_P2PKH
        )
        self.assertEqual(bytes(script), bytes(expected))

    def test_name_new_p2sh(self):
        commitment = b"\xab" * 20
        script = output_script_name_new(commitment, INNER_P2SH)
        expected = b"\x51" + b"\x14" + commitment + b"\x6d" + INNER_P2SH
        self.assertEqual(bytes(script), bytes(expected))

    def test_name_new_rejects_bad_hash(self):
        with self.assertRaises(Exception):
            output_script_name_new(b"\x00" * 19, INNER_P2PKH)
        with self.assertRaises(Exception):
            output_script_name_new(b"\x00" * 21, INNER_P2PKH)

    def test_name_firstupdate_short(self):
        name = b"d/example"
        rand = b"\x02" * 20
        value = b'{"ip":"1.2.3.4"}'
        script = output_script_name_firstupdate(name, rand, value, INNER_P2PKH)
        # OP_2 + push(name) + push(rand) + push(value)
        # + OP_2DROP OP_2DROP OP_DROP + inner
        expected = (
            b"\x52"
            + bytes([len(name)]) + name
            + b"\x14" + rand
            + bytes([len(value)]) + value
            + b"\x6d\x6d\x75"
            + INNER_P2PKH
        )
        self.assertEqual(bytes(script), bytes(expected))

    def test_name_firstupdate_long_value_uses_pushdata1(self):
        # value of 80 bytes -> OP_PUSHDATA1 (0x4c) <len> <data>.
        name = b"d/longvalue"
        rand = b"\x05" * 20
        value = b"x" * 80
        script = output_script_name_firstupdate(name, rand, value, INNER_P2PKH)
        # Find the value push: it's the third push after OP_2 + name push + rand push.
        # We verify the byte sequence directly.
        expected = (
            b"\x52"
            + bytes([len(name)]) + name
            + b"\x14" + rand
            + b"\x4c" + bytes([len(value)]) + value
            + b"\x6d\x6d\x75"
            + INNER_P2PKH
        )
        self.assertEqual(bytes(script), bytes(expected))

    def test_name_firstupdate_rejects_bad_rand(self):
        with self.assertRaises(Exception):
            output_script_name_firstupdate(
                b"d/x", b"\x00" * 19, b"v", INNER_P2PKH
            )

    def test_name_firstupdate_rejects_empty_name(self):
        with self.assertRaises(Exception):
            output_script_name_firstupdate(
                b"", b"\x00" * 20, b"v", INNER_P2PKH
            )

    def test_name_firstupdate_rejects_oversized_name(self):
        with self.assertRaises(Exception):
            output_script_name_firstupdate(
                b"x" * 256, b"\x00" * 20, b"v", INNER_P2PKH
            )

    def test_name_firstupdate_rejects_oversized_value(self):
        with self.assertRaises(Exception):
            output_script_name_firstupdate(
                b"d/x", b"\x00" * 20, b"v" * 521, INNER_P2PKH
            )

    def test_name_update_short(self):
        name = b"d/example"
        value = b'{"ip":"5.6.7.8"}'
        script = output_script_name_update(name, value, INNER_P2PKH)
        expected = (
            b"\x53"
            + bytes([len(name)]) + name
            + bytes([len(value)]) + value
            + b"\x6d\x75"
            + INNER_P2PKH
        )
        self.assertEqual(bytes(script), bytes(expected))

    def test_name_update_max_value_uses_pushdata2(self):
        # 520-byte value -> OP_PUSHDATA2 (0x4d) <lenLE>.
        name = b"d/maxvalue"
        value = b"y" * 520
        script = output_script_name_update(name, value, INNER_P2PKH)
        expected = (
            b"\x53"
            + bytes([len(name)]) + name
            + b"\x4d" + bytes([520 & 0xFF, (520 >> 8) & 0xFF]) + value
            + b"\x6d\x75"
            + INNER_P2PKH
        )
        self.assertEqual(bytes(script), bytes(expected))

    def test_name_update_rejects_empty_name(self):
        with self.assertRaises(Exception):
            output_script_name_update(b"", b"v", INNER_P2PKH)

    def test_name_update_rejects_oversized_value(self):
        with self.assertRaises(Exception):
            output_script_name_update(b"d/x", b"v" * 521, INNER_P2PKH)


if __name__ == "__main__":
    unittest.main()
