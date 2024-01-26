from common import *  # isort:skip

import apps.common.writers as writers


class TestSeed(unittest.TestCase):
    def test_write_uint8(self):
        buf = bytearray()
        writers.write_uint8(buf, 0x12)
        self.assertEqual(buf, b"\x12")

    def test_write_uint16_le(self):
        buf = bytearray()
        writers.write_uint16_le(buf, 0x1234)
        self.assertEqual(buf, b"\x34\x12")

    def test_write_uint16_le_overflow(self):
        buf = bytearray()
        with self.assertRaises(AssertionError):
            writers.write_uint16_le(buf, 0x12345678)

    def test_write_uint32_le(self):
        buf = bytearray()
        writers.write_uint32_le(buf, 0x12345678)
        self.assertEqual(buf, b"\x78\x56\x34\x12")

    def test_write_uint64_le(self):
        buf = bytearray()
        writers.write_uint64_le(buf, 0x1234567890ABCDEF)
        self.assertEqual(buf, b"\xef\xcd\xab\x90\x78\x56\x34\x12")

    def test_write_uint32_be(self):
        buf = bytearray()
        writers.write_uint32_be(buf, 0x12345678)
        self.assertEqual(buf, b"\x12\x34\x56\x78")

    def test_write_uint64_be(self):
        buf = bytearray()
        writers.write_uint64_be(buf, 0x1234567890ABCDEF)
        self.assertEqual(buf, b"\x12\x34\x56\x78\x90\xab\xcd\xef")


if __name__ == "__main__":
    unittest.main()
