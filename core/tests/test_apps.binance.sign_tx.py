from common import *

from apps.binance.helpers import produce_json_for_signing
from apps.binance.sign_tx import generate_content_signature, sign_tx

from trezor.crypto.curve import secp256k1
from trezor.crypto.hashlib import sha256
from trezor.messages.BinanceCancelMsg import BinanceCancelMsg
from trezor.messages.BinanceCoin import BinanceCoin
from trezor.messages.BinanceInputOutput import BinanceInputOutput
from trezor.messages.BinanceOrderMsg import BinanceOrderMsg
from trezor.messages.BinanceSignTx import BinanceSignTx
from trezor.messages.BinanceTransferMsg import BinanceTransferMsg


class TestBinanceSign(unittest.TestCase):    
    def test_order_signature(self):
        # source of testing data
        # https://github.com/binance-chain/javascript-sdk/blob/master/__tests__/fixtures/placeOrder.json
        json_hex_msg = "7b226163636f756e745f6e756d626572223a223334222c22636861696e5f6964223a2242696e616e63652d436861696e2d4e696c65222c2264617461223a6e756c6c2c226d656d6f223a22222c226d736773223a5b7b226964223a22424133364630464144373444384634313034353436334534373734463332384634414637373945352d3333222c226f7264657274797065223a322c227072696365223a3130303030303030302c227175616e74697479223a3130303030303030302c2273656e646572223a2274626e623168676d3070376b68666b38357a707a3576306a38776e656a33613930773730397a7a6c666664222c2273696465223a312c2273796d626f6c223a224144412e422d4236335f424e42222c2274696d65696e666f726365223a317d5d2c2273657175656e6365223a223332222c22736f75726365223a2231227d"
        expected_signature = "851fc9542342321af63ecbba7d3ece545f2a42bad01ba32cff5535b18e54b6d3106e10b6a4525993d185a1443d9a125186960e028eabfdd8d76cf70a3a7e3100"
        public_key = "029729a52e4e3c2b4a4e52aa74033eedaf8ba1df5ab6d1f518fd69e67bbd309b0e"
        private_key = "90335b9d2153ad1a9799a3ccc070bd64b4164e9642ee1dd48053c33f9a3a05e9"

        # Testing data for object creation is decoded from json_hex_msg
        envelope = BinanceSignTx(msg_count=1, account_number=34, chain_id="Binance-Chain-Nile", memo="", sequence=32, source=1)
        msg = BinanceOrderMsg(id="BA36F0FAD74D8F41045463E4774F328F4AF779E5-33",
                              ordertype=2,
                              price=100000000,
                              quantity=100000000,
                              sender="tbnb1hgm0p7khfk85zpz5v0j8wnej3a90w709zzlffd",
                              side=1,
                              symbol="ADA.B-B63_BNB",
                              timeinforce=1)

        msg_json = produce_json_for_signing(envelope, msg)

        #check if our json string produced for signing is the same as test vector
        self.assertEqual(hexlify(msg_json).decode(), json_hex_msg)

        #verify signature against public key
        signature = generate_content_signature(msg_json.encode(), unhexlify(private_key))
        self.assertTrue(verify_content_signature(unhexlify(public_key), signature, unhexlify(json_hex_msg)))

        #check if the signed data is the same as test vector
        self.assertEqual(signature, unhexlify(expected_signature))

    def test_cancel_signature(self):
        # source of testing data 
        # https://github.com/binance-chain/javascript-sdk/blob/master/__tests__/fixtures/cancelOrder.json
        json_hex_msg = "7b226163636f756e745f6e756d626572223a223334222c22636861696e5f6964223a2242696e616e63652d436861696e2d4e696c65222c2264617461223a6e756c6c2c226d656d6f223a22222c226d736773223a5b7b227265666964223a22424133364630464144373444384634313034353436334534373734463332384634414637373945352d3239222c2273656e646572223a2274626e623168676d3070376b68666b38357a707a3576306a38776e656a33613930773730397a7a6c666664222c2273796d626f6c223a2242434853562e422d3130465f424e42227d5d2c2273657175656e6365223a223333222c22736f75726365223a2231227d"
        expected_signature = "d93fb0402b2b30e7ea08e123bb139ad68bf0a1577f38592eb22d11e127f09bbd3380f29b4bf15bdfa973454c5c8ed444f2e256e956fe98cfd21e886a946e21e5"
        public_key = "029729a52e4e3c2b4a4e52aa74033eedaf8ba1df5ab6d1f518fd69e67bbd309b0e"
        private_key = "90335b9d2153ad1a9799a3ccc070bd64b4164e9642ee1dd48053c33f9a3a05e9"

        # Testing data for object creation is decoded from json_hex_msg
        envelope = BinanceSignTx(msg_count=1, account_number=34, chain_id="Binance-Chain-Nile", memo="", sequence=33, source=1)
        msg = BinanceCancelMsg(refid="BA36F0FAD74D8F41045463E4774F328F4AF779E5-29",
                               sender="tbnb1hgm0p7khfk85zpz5v0j8wnej3a90w709zzlffd",
                               symbol="BCHSV.B-10F_BNB")

        msg_json = produce_json_for_signing(envelope, msg)

        #check if our json string produced for signing is the same as test vector
        self.assertEqual(hexlify(msg_json).decode(), json_hex_msg)

        #verify signature against public key
        signature = generate_content_signature(msg_json.encode(), unhexlify(private_key))
        self.assertTrue(verify_content_signature(unhexlify(public_key), signature, unhexlify(json_hex_msg)))

        #check if the signed data is the same as test vector
        self.assertEqual(signature, unhexlify(expected_signature))

    def test_transfer_signature(self):
        # source of testing data 
        # https://github.com/binance-chain/javascript-sdk/blob/master/__tests__/fixtures/transfer.json        
        json_hex_msg = "7b226163636f756e745f6e756d626572223a223334222c22636861696e5f6964223a2242696e616e63652d436861696e2d4e696c65222c2264617461223a6e756c6c2c226d656d6f223a2274657374222c226d736773223a5b7b22696e70757473223a5b7b2261646472657373223a2274626e623168676d3070376b68666b38357a707a3576306a38776e656a33613930773730397a7a6c666664222c22636f696e73223a5b7b22616d6f756e74223a2231303030303030303030222c2264656e6f6d223a22424e42227d5d7d5d2c226f757470757473223a5b7b2261646472657373223a2274626e6231737335376538736137786e77713033306b3263747237373575616339676a7a676c7168767079222c22636f696e73223a5b7b22616d6f756e74223a2231303030303030303030222c2264656e6f6d223a22424e42227d5d7d5d7d5d2c2273657175656e6365223a223331222c22736f75726365223a2231227d"
        expected_signature = "97b4c2e41b0d0f61ddcf4020fff0ecb227d6df69b3dd7e657b34be0e32b956e22d0c6be5832d25353ae24af0bb223d4a5337320518c4e7708b84c8e05eb6356b"
        public_key = "029729a52e4e3c2b4a4e52aa74033eedaf8ba1df5ab6d1f518fd69e67bbd309b0e"
        private_key = "90335b9d2153ad1a9799a3ccc070bd64b4164e9642ee1dd48053c33f9a3a05e9"

        # Testing data for object creation is decoded from json_hex_msg
        envelope = BinanceSignTx(msg_count=1, account_number=34, chain_id="Binance-Chain-Nile", memo="test", sequence=31, source=1)
        coin = BinanceCoin(denom="BNB", amount=1000000000)
        first_input = BinanceInputOutput(address="tbnb1hgm0p7khfk85zpz5v0j8wnej3a90w709zzlffd", coins=[coin])
        first_output = BinanceInputOutput(address="tbnb1ss57e8sa7xnwq030k2ctr775uac9gjzglqhvpy", coins=[coin])
        msg = BinanceTransferMsg(inputs=[first_input], outputs=[first_output])

        msg_json = produce_json_for_signing(envelope, msg)

        #check if our json string produced for signing is the same as test vector
        self.assertEqual(hexlify(msg_json).decode(), json_hex_msg)

        #verify signature against public key
        signature = generate_content_signature(msg_json.encode(), unhexlify(private_key))
        self.assertTrue(verify_content_signature(unhexlify(public_key), signature, unhexlify(json_hex_msg)))

        #check if the signed data is the same as test vector
        self.assertEqual(signature, unhexlify(expected_signature))

def verify_content_signature(
    public_key: bytes, signature: bytes, unsigned_data: bytes
) -> bool:
    msghash = sha256(unsigned_data).digest()
    return secp256k1.verify(public_key, signature, msghash)

if __name__ == '__main__':
    unittest.main()
