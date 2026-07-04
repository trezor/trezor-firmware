# flake8: noqa: F403,F405
from common import *  # isort:skip

if not utils.BITCOIN_ONLY:
    from apps.stellar.writers import write_int32, write_int64


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestStellarWriters(unittest.TestCase):
    def test_write_int32(self):
        TESTS = [
            (0, "00000000"),
            (1, "00000001"),
            (127, "0000007f"),
            (256, "00000100"),
            (-1, "ffffffff"),
            (-128, "ffffff80"),
            (-256, "ffffff00"),
            (0x7FFFFFFF, "7fffffff"),  # INT32_MAX
            (-0x80000000, "80000000"),  # INT32_MIN
        ]
        for value, expected in TESTS:
            w = bytearray()
            write_int32(w, value)
            self.assertEqual(w, unhexlify(expected), msg=f"write_int32({value})")

    def test_write_int32_out_of_range(self):
        TESTS = [
            0x80000000,  # INT32_MAX + 1
            -0x80000001,  # INT32_MIN - 1
            0x100000000,  # way out of range
        ]
        for value in TESTS:
            w = bytearray()
            with self.assertRaises(ValueError):
                write_int32(w, value)

    def test_write_int64(self):
        TESTS = [
            (0, "0000000000000000"),
            (1, "0000000000000001"),
            (127, "000000000000007f"),
            (0x100000000, "0000000100000000"),  # larger than int32
            (-1, "ffffffffffffffff"),
            (-128, "ffffffffffffff80"),
            (-0x100000000, "ffffffff00000000"),
            (0x7FFFFFFFFFFFFFFF, "7fffffffffffffff"),  # INT64_MAX
            (-0x8000000000000000, "8000000000000000"),  # INT64_MIN
        ]
        for value, expected in TESTS:
            w = bytearray()
            write_int64(w, value)
            self.assertEqual(w, unhexlify(expected), msg=f"write_int64({value})")

    def test_write_int64_out_of_range(self):
        TESTS = [
            0x8000000000000000,  # INT64_MAX + 1
            -0x8000000000000001,  # INT64_MIN - 1
            0x10000000000000000,  # way out of range
        ]
        for value in TESTS:
            w = bytearray()
            with self.assertRaises(ValueError):
                write_int64(w, value)


if __name__ == "__main__":
    unittest.main()
