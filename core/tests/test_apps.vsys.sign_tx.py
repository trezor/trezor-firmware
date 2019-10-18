from common import *
from trezor.crypto.curve import ed25519
from trezor.crypto.curve import curve25519
from trezor.crypto import base58

if not utils.BITCOIN_ONLY:
    from apps.vsys.sign_tx import *
    from trezor.messages.VsysSignTx import VsysSignTx
    from apps.vsys.constants import *


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestVsysSign(unittest.TestCase):

    def test_payment_signature(self):
        private_key = "8Yoy9QL2sqggrM22VvHcRmAVzRr5h23FuDeFohyAU27B"
        public_key = "2cLDxAPJNWGGWAyHUFEnyoznhkf4QCEkcQrL5g2oEBCY"
        private_key_bytes = base58.decode(private_key)
        public_key_bytes = base58.decode(public_key)
        msg = VsysSignTx(
            transactionType=PAYMENT_TX_TYPE,
            senderPublicKey=public_key,
            amount=1000000000,
            fee=10000000,
            feeScale=100,
            recipient="AU6GsBinGPqW8zUuvmjgwpBNLfyyTU3p83Q",
            timestamp=1547722056762119200,
            attachment="HXRC"
        )

        to_sign_bytes = encode_payment_tx_to_bytes(msg)
        expect_to_sign = [0x02, 0x15, 0x7a, 0x9d, 0x02, 0xac, 0x57, 0xd4, 0x20, 0x00, 0x00, 0x00, 0x00, 0x3b, 0x9a,
                          0xca, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x98, 0x96, 0x80, 0x00, 0x64, 0x05, 0x54, 0x9c,
                          0x6d, 0xf7, 0xb3, 0x76, 0x77, 0x1b, 0x19, 0xff, 0x3b, 0xdb, 0x58, 0xd0, 0x4b, 0x49, 0x99,
                          0x91, 0x66, 0x3c, 0x47, 0x44, 0x4e, 0x42, 0x5f, 0x00, 0x03, 0x31, 0x32, 0x33]
        self.assertEqual(to_sign_bytes, bytearray(expect_to_sign))
        signature = generate_content_signature(to_sign_bytes, private_key_bytes)
        self.assertTrue(verify_content_signature(to_sign_bytes, public_key_bytes, signature))

    def test_lease_signature(self):
        private_key = "8Yoy9QL2sqggrM22VvHcRmAVzRr5h23FuDeFohyAU27B"
        public_key = "2cLDxAPJNWGGWAyHUFEnyoznhkf4QCEkcQrL5g2oEBCY"
        private_key_bytes = base58.decode(private_key)
        public_key_bytes = base58.decode(public_key)
        msg = VsysSignTx(
            transactionType=LEASE_TX_TYPE,
            senderPublicKey=public_key,
            amount=1000000000,
            fee=10000000,
            feeScale=100,
            recipient="AU6GsBinGPqW8zUuvmjgwpBNLfyyTU3p83Q",
            timestamp=1547722056762119200
        )

        to_sign_bytes = encode_lease_tx_to_bytes(msg)
        expect_to_sign = [0x03, 0x05, 0x54, 0x9c, 0x6d, 0xf7, 0xb3, 0x76, 0x77, 0x1b, 0x19, 0xff, 0x3b, 0xdb, 0x58,
                          0xd0, 0x4b, 0x49, 0x99, 0x91, 0x66, 0x3c, 0x47, 0x44, 0x4e, 0x42, 0x5f, 0x00, 0x00, 0x00,
                          0x00, 0x3b, 0x9a, 0xca, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x98, 0x96, 0x80, 0x00, 0x64,
                          0x15, 0x7a, 0x9d, 0x02, 0xac, 0x57, 0xd4, 0x20]
        self.assertEqual(to_sign_bytes, bytearray(expect_to_sign))
        signature = generate_content_signature(to_sign_bytes, private_key_bytes)
        self.assertTrue(verify_content_signature(to_sign_bytes, public_key_bytes, signature))

    def test_cancel_lease_signature(self):
        private_key = "8Yoy9QL2sqggrM22VvHcRmAVzRr5h23FuDeFohyAU27B"
        public_key = "2cLDxAPJNWGGWAyHUFEnyoznhkf4QCEkcQrL5g2oEBCY"
        private_key_bytes = base58.decode(private_key)
        public_key_bytes = base58.decode(public_key)
        msg = VsysSignTx(
            transactionType=LEASE_CANCEL_TX_TYPE,
            senderPublicKey=public_key,
            fee=10000000,
            feeScale=100,
            txId="8XC9UFcf1yWrFiWWtjiSnCqXhyuwzzw5SE7DrNuiE8gF",
            timestamp=1547722056762119200
        )

        to_sign_bytes = encode_cancel_lease_tx_to_bytes(msg)
        expect_to_sign = [0x04, 0x00, 0x00, 0x00, 0x00, 0x00, 0x98, 0x96, 0x80, 0x00, 0x64, 0x15, 0x7a, 0x9d, 0x02,
                          0xac, 0x57, 0xd4, 0x20, 0x6f, 0xbd, 0xd5, 0xea, 0xe3, 0xe3, 0xa4, 0x8e, 0x7d, 0xe8, 0x14,
                          0x08, 0x4f, 0xf3, 0x4f, 0xd3, 0xf9, 0xaf, 0x97, 0x0e, 0xbf, 0x4a, 0x30, 0x82, 0xad, 0x32,
                          0xa5, 0x88, 0x09, 0x3c, 0xde, 0xb8]
        self.assertEqual(to_sign_bytes, bytearray(expect_to_sign))
        signature = generate_content_signature(to_sign_bytes, private_key_bytes)
        self.assertTrue(verify_content_signature(to_sign_bytes, public_key_bytes, signature))

if __name__ == '__main__':
    unittest.main()
