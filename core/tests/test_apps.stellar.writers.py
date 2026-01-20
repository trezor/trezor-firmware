# flake8: noqa: F403,F405
from common import *  # isort:skip

if not utils.BITCOIN_ONLY:
    from apps.stellar.writers import write_int32, write_int64


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestStellarWriters(unittest.TestCase):
    def test_write_int32(self):
        w = bytearray()
        write_int32(w, 0)
        self.assertEqual(w, unhexlify("00000000"))

        w = bytearray()
        write_int32(w, 1)
        self.assertEqual(w, unhexlify("00000001"))

        w = bytearray()
        write_int32(w, 127)
        self.assertEqual(w, unhexlify("0000007f"))

        w = bytearray()
        write_int32(w, 256)
        self.assertEqual(w, unhexlify("00000100"))

        w = bytearray()
        write_int32(w, -1)
        self.assertEqual(w, unhexlify("ffffffff"))

        w = bytearray()
        write_int32(w, -128)
        self.assertEqual(w, unhexlify("ffffff80"))

        w = bytearray()
        write_int32(w, -256)
        self.assertEqual(w, unhexlify("ffffff00"))

        w = bytearray()
        write_int32(w, 0x7FFFFFFF)  # INT32_MAX
        self.assertEqual(w, unhexlify("7fffffff"))

        w = bytearray()
        write_int32(w, -0x80000000)  # INT32_MIN
        self.assertEqual(w, unhexlify("80000000"))

    def test_write_int32_out_of_range(self):
        w = bytearray()
        with self.assertRaises(ValueError):
            write_int32(w, 0x80000000)  # INT32_MAX + 1

        with self.assertRaises(ValueError):
            write_int32(w, -0x80000001)  # INT32_MIN - 1

        with self.assertRaises(ValueError):
            write_int32(w, 0x100000000)  # way out of range

    def test_write_int64(self):
        w = bytearray()
        write_int64(w, 0)
        self.assertEqual(w, unhexlify("0000000000000000"))

        w = bytearray()
        write_int64(w, 1)
        self.assertEqual(w, unhexlify("0000000000000001"))

        w = bytearray()
        write_int64(w, 127)
        self.assertEqual(w, unhexlify("000000000000007f"))

        w = bytearray()
        write_int64(w, 0x100000000)  # larger than int32
        self.assertEqual(w, unhexlify("0000000100000000"))

        w = bytearray()
        write_int64(w, -1)
        self.assertEqual(w, unhexlify("ffffffffffffffff"))

        w = bytearray()
        write_int64(w, -128)
        self.assertEqual(w, unhexlify("ffffffffffffff80"))

        w = bytearray()
        write_int64(w, -0x100000000)
        self.assertEqual(w, unhexlify("ffffffff00000000"))

        w = bytearray()
        write_int64(w, 0x7FFFFFFFFFFFFFFF)  # INT64_MAX
        self.assertEqual(w, unhexlify("7fffffffffffffff"))

        w = bytearray()
        write_int64(w, -0x8000000000000000)  # INT64_MIN
        self.assertEqual(w, unhexlify("8000000000000000"))

    def test_write_int64_out_of_range(self):
        w = bytearray()
        with self.assertRaises(ValueError):
            write_int64(w, 0x8000000000000000)  # INT64_MAX + 1

        with self.assertRaises(ValueError):
            write_int64(w, -0x8000000000000001)  # INT64_MIN - 1

        with self.assertRaises(ValueError):
            write_int64(w, 0x10000000000000000)  # way out of range


if __name__ == "__main__":
    unittest.main()
