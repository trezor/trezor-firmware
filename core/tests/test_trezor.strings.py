from common import *

from trezor import strings


class TestStrings(unittest.TestCase):

    def test_format_amount(self):
        VECTORS = [
            (123456, 3, "123.456"),
            (4242, 7, "0.0004242"),
            (-123456, 3, "-123.456"),
            (-4242, 7, "-0.0004242"),
        ]
        for v in VECTORS:
            self.assertEqual(strings.format_amount(v[0], v[1]), v[2])


    def test_format_plural(self):
        VECTORS = [
            ("We need {count} more {plural}", 3, "share", "We need 3 more shares"),
            ("We need {count} more {plural}", 1, "share", "We need 1 more share"),
            ("We need {count} more {plural}", 1, "candy", "We need 1 more candy"),
            ("We need {count} more {plural}", 7, "candy", "We need 7 more candies"),
        ]
        for v in VECTORS:
            self.assertEqual(strings.format_plural(v[0], v[1], v[2]), v[3])

        with self.assertRaises(ValueError):
            strings.format_plural("Hello", 1, "share")


if __name__ == '__main__':
    unittest.main()
