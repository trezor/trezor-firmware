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

# A canonical P2WPKH inner script: OP_0 <push20 program>.
INNER_P2WPKH = unhexlify("0014" + "22" * 20)

# A canonical P2WSH inner script: OP_0 <push32 program>.
INNER_P2WSH = unhexlify("0020" + "33" * 32)


class TestScriptsNamecoin(unittest.TestCase):
    def test_name_new_p2pkh(self):
        commitment = b"\x01" * 20
        script = output_script_name_new(commitment, INNER_P2PKH)
        # OP_1 (0x51) + push20 (0x14) + 20 bytes + OP_2DROP (0x6d) + inner
        expected = b"\x51" + b"\x14" + commitment + b"\x6d" + INNER_P2PKH
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
            + bytes([len(name)])
            + name
            + b"\x14"
            + rand
            + bytes([len(value)])
            + value
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
            + bytes([len(name)])
            + name
            + b"\x14"
            + rand
            + b"\x4c"
            + bytes([len(value)])
            + value
            + b"\x6d\x6d\x75"
            + INNER_P2PKH
        )
        self.assertEqual(bytes(script), bytes(expected))

    def test_name_firstupdate_rejects_bad_rand(self):
        with self.assertRaises(Exception):
            output_script_name_firstupdate(b"d/x", b"\x00" * 19, b"v", INNER_P2PKH)

    def test_name_firstupdate_rejects_empty_name(self):
        with self.assertRaises(Exception):
            output_script_name_firstupdate(b"", b"\x00" * 20, b"v", INNER_P2PKH)

    def test_name_firstupdate_rejects_oversized_name(self):
        with self.assertRaises(Exception):
            output_script_name_firstupdate(b"x" * 256, b"\x00" * 20, b"v", INNER_P2PKH)

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
            + bytes([len(name)])
            + name
            + bytes([len(value)])
            + value
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
            + bytes([len(name)])
            + name
            + b"\x4d"
            + bytes([520 & 0xFF, (520 >> 8) & 0xFF])
            + value
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

    # ----- Segwit inner-script coverage --------------------------------

    def test_name_new_p2wpkh(self):
        commitment = b"\xcd" * 20
        script = output_script_name_new(commitment, INNER_P2WPKH)
        # OP_1 + push20 + commitment + OP_2DROP + P2WPKH inner.
        expected = b"\x51\x14" + commitment + b"\x6d" + INNER_P2WPKH
        self.assertEqual(bytes(script), bytes(expected))

    def test_name_new_p2wsh(self):
        commitment = b"\xef" * 20
        script = output_script_name_new(commitment, INNER_P2WSH)
        expected = b"\x51\x14" + commitment + b"\x6d" + INNER_P2WSH
        self.assertEqual(bytes(script), bytes(expected))

    def test_name_firstupdate_p2wpkh(self):
        name = b"d/segwit"
        rand = b"\x07" * 20
        value = b'{"info":"segwit name"}'
        script = output_script_name_firstupdate(name, rand, value, INNER_P2WPKH)
        expected = (
            b"\x52"
            + bytes([len(name)])
            + name
            + b"\x14"
            + rand
            + bytes([len(value)])
            + value
            + b"\x6d\x6d\x75"
            + INNER_P2WPKH
        )
        self.assertEqual(bytes(script), bytes(expected))

    def test_name_update_p2wpkh(self):
        name = b"d/segwit"
        value = b'{"info":"updated"}'
        script = output_script_name_update(name, value, INNER_P2WPKH)
        expected = (
            b"\x53"
            + bytes([len(name)])
            + name
            + bytes([len(value)])
            + value
            + b"\x6d\x75"
            + INNER_P2WPKH
        )
        self.assertEqual(bytes(script), bytes(expected))


class TestOutputDeriveNameOpScriptInnerGuard(unittest.TestCase):
    """Cover the inner-script structural check in scripts.output_derive_name_op_script.

    The function itself depends on output_derive_script + a real coin def,
    which we don't have inside a MicroPython unit test context. We test the
    structural predicate _is_namecoin_inner_script directly so the guard
    rejects unexpected shapes (notably witness v1 / taproot).
    """

    def test_predicate_accepts_p2pkh(self):
        from apps.bitcoin.scripts import _is_namecoin_inner_script

        self.assertTrue(_is_namecoin_inner_script(INNER_P2PKH))

    def test_predicate_accepts_p2sh(self):
        from apps.bitcoin.scripts import _is_namecoin_inner_script

        self.assertTrue(_is_namecoin_inner_script(INNER_P2SH))

    def test_predicate_accepts_p2wpkh(self):
        from apps.bitcoin.scripts import _is_namecoin_inner_script

        self.assertTrue(_is_namecoin_inner_script(INNER_P2WPKH))

    def test_predicate_accepts_p2wsh(self):
        from apps.bitcoin.scripts import _is_namecoin_inner_script

        self.assertTrue(_is_namecoin_inner_script(INNER_P2WSH))

    def test_predicate_rejects_taproot(self):
        # Witness v1 (taproot): OP_1 (0x51) push32 (0x20) + 32-byte program.
        taproot = b"\x51\x20" + b"\x44" * 32
        from apps.bitcoin.scripts import _is_namecoin_inner_script

        self.assertFalse(_is_namecoin_inner_script(taproot))

    def test_predicate_rejects_op_return(self):
        # OP_RETURN <push5> 'hello'.
        op_return = b"\x6a\x05hello"
        from apps.bitcoin.scripts import _is_namecoin_inner_script

        self.assertFalse(_is_namecoin_inner_script(op_return))

    def test_predicate_rejects_short_p2pkh(self):
        # Missing trailing OP_EQUALVERIFY OP_CHECKSIG.
        truncated = b"\x76\xa9\x14" + b"\x00" * 20
        from apps.bitcoin.scripts import _is_namecoin_inner_script

        self.assertFalse(_is_namecoin_inner_script(truncated))

    def test_predicate_rejects_witness_v0_wrong_length(self):
        # Witness v0 with a 30-byte program (neither P2WPKH nor P2WSH).
        weird = b"\x00\x1e" + b"\x55" * 30
        from apps.bitcoin.scripts import _is_namecoin_inner_script

        self.assertFalse(_is_namecoin_inner_script(weird))

    def test_predicate_rejects_empty(self):
        from apps.bitcoin.scripts import _is_namecoin_inner_script

        self.assertFalse(_is_namecoin_inner_script(b""))


if __name__ == "__main__":
    unittest.main()
