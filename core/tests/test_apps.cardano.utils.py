from common import *

if not utils.BITCOIN_ONLY:
    from apps.cardano.helpers.utils import variable_length_encode, format_asset_fingerprint


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

    def test_format_asset_fingerprint(self):
        # source: https://github.com/cardano-foundation/CIPs/pull/64
        test_vectors = [
            (("7eae28af2208be856f7a119668ae52a49b73725e326dc16579dcc373", ""), "asset1rjklcrnsdzqp65wjgrg55sy9723kw09mlgvlc3"),
            (("7eae28af2208be856f7a119668ae52a49b73725e326dc16579dcc373", "504154415445"), "asset13n25uv0yaf5kus35fm2k86cqy60z58d9xmde92"),
            (("1e349c9bdea19fd6c147626a5260bc44b71635f398b67c59881df209", "7eae28af2208be856f7a119668ae52a49b73725e326dc16579dcc373"), "asset1aqrdypg669jgazruv5ah07nuyqe0wxjhe2el6f"),
        ]

        for params, expected in test_vectors:
            actual = format_asset_fingerprint(policy_id=unhexlify(params[0]), asset_name_bytes=unhexlify(params[1]))
            self.assertEqual(actual, expected)


if __name__ == '__main__':
    unittest.main()
