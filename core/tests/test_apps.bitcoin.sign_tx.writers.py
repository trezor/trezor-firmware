from common import *

from trezor.messages import TxInput
from trezor.enums import InputScriptType

from apps.bitcoin import writers


class TestWriters(unittest.TestCase):
    def test_tx_input(self):
        inp = TxInput(
            address_n=[0],
            amount=390000,
            prev_hash=unhexlify(
                "d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882"
            ),
            prev_index=0,
            sequence=0xffffffff,
            script_sig=b"0123456789",
        )

        b = bytearray()
        writers.write_tx_input(b, inp, inp.script_sig)
        self.assertEqual(len(b), 32 + 4 + 1 + 10 + 4)

        for bad_prevhash in (b"", b"x", b"hello", b"x" * 33):
            inp.prev_hash = bad_prevhash
            self.assertRaises(AssertionError, writers.write_tx_input, b, inp, inp.script_sig)

    def test_tx_input_check(self):
        inp = TxInput(
            address_n=[0],
            amount=390000,
            prev_hash=unhexlify(
                "d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882"
            ),
            prev_index=0,
            script_type=InputScriptType.SPENDWITNESS,
            sequence=0xffffffff,
            script_pubkey=unhexlify("76a91424a56db43cf6f2b02e838ea493f95d8d6047423188ac"),
            script_sig=b"0123456789",
        )

        b = bytearray()
        writers.write_tx_input_check(b, inp)
        self.assertEqual(len(b), 32 + 4 + 4 + 4 + 4 + 4 + 8 + 26)

        for bad_prevhash in (b"", b"x", b"hello", b"x" * 33):
            inp.prev_hash = bad_prevhash
            self.assertRaises(AssertionError, writers.write_tx_input_check, b, inp)

if __name__ == "__main__":
    unittest.main()
