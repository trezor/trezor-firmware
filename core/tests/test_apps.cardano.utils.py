from common import *

if not utils.BITCOIN_ONLY:
    from apps.cardano.helpers.utils import variable_length_encode


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestCardanoUtils(unittest.TestCase):
    def test_variable_length_encode(self):
        test_vectors = [
            (0, bytes([0x00])), 
            (42, bytes([0x2A])), 
            (127, bytes([0x7F])), 
            (128, bytes([0x81, 0x00])),
            (129, bytes([0x81, 0x01])),
            (255, bytes([0x81, 0x7F])),
            (256, bytes([0x82, 0x00])),
            (16383, bytes([0xFF, 0x7F])),
            (16384, bytes([0x81, 0x80, 0x00])),
        ]

        for number, expected in test_vectors:
            actual = variable_length_encode(number)
            self.assertEqual(actual, expected)


    def test_variable_length_encode_negative_number(self):
        with self.assertRaises(ValueError):
            variable_length_encode(-1)


if __name__ == '__main__':
    unittest.main()
