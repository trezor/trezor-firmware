from common import *

from trezor import utils


class TestUtils(unittest.TestCase):

    def test_chunks(self):
        c = list(utils.chunks(range(100), 7))
        for i in range(15):
            # need to check start, stop, step attrs until https://github.com/micropython/micropython/issues/2600 is resolved
            self.assertEqual(c[i].start, i * 7)
            self.assertEqual(c[i].stop, 100 if (i == 14) else (i + 1) * 7)
            self.assertEqual(c[i].step, 1)

    def test_truncate_utf8(self):
        self.assertEqual(utils.truncate_utf8("", 3), "")
        self.assertEqual(utils.truncate_utf8("a", 3), "a")
        self.assertEqual(utils.truncate_utf8("ab", 3), "ab")
        self.assertEqual(utils.truncate_utf8("abc", 3), "abc")
        self.assertEqual(utils.truncate_utf8("abcd", 3), "abc")
        self.assertEqual(utils.truncate_utf8("abcde", 3), "abc")
        self.assertEqual(utils.truncate_utf8("a\u0123", 3), "a\u0123")  # b'a\xc4\xa3'
        self.assertEqual(utils.truncate_utf8("a\u1234", 3), "a")  # b'a\xe1\x88\xb4'
        self.assertEqual(utils.truncate_utf8("ab\u0123", 3), "ab")  # b'ab\xc4\xa3'
        self.assertEqual(utils.truncate_utf8("ab\u1234", 3), "ab")  # b'ab\xe1\x88\xb4'
        self.assertEqual(utils.truncate_utf8("abc\u0123", 3), "abc")  # b'abc\xc4\xa3'
        self.assertEqual(utils.truncate_utf8("abc\u1234", 3), "abc")  # b'abc\xe1\x88\xb4'
        self.assertEqual(utils.truncate_utf8("\u1234\u5678", 0), "")  # b'\xe1\x88\xb4\xe5\x99\xb8
        self.assertEqual(utils.truncate_utf8("\u1234\u5678", 1), "")  # b'\xe1\x88\xb4\xe5\x99\xb8
        self.assertEqual(utils.truncate_utf8("\u1234\u5678", 2), "")  # b'\xe1\x88\xb4\xe5\x99\xb8
        self.assertEqual(utils.truncate_utf8("\u1234\u5678", 3), "\u1234")  # b'\xe1\x88\xb4\xe5\x99\xb8
        self.assertEqual(utils.truncate_utf8("\u1234\u5678", 4), "\u1234")  # b'\xe1\x88\xb4\xe5\x99\xb8
        self.assertEqual(utils.truncate_utf8("\u1234\u5678", 5), "\u1234")  # b'\xe1\x88\xb4\xe5\x99\xb8
        self.assertEqual(utils.truncate_utf8("\u1234\u5678", 6), "\u1234\u5678")  # b'\xe1\x88\xb4\xe5\x99\xb8
        self.assertEqual(utils.truncate_utf8("\u1234\u5678", 7), "\u1234\u5678")  # b'\xe1\x88\xb4\xe5\x99\xb8


if __name__ == '__main__':
    unittest.main()
