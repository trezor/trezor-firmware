from common import *

from trezor.crypto.curve import secp256k1
from trezor.crypto.hashlib import sha256

if not utils.BITCOIN_ONLY:
    from apps.binance.helpers import produce_json_for_signing
    from apps.binance.sign_tx import generate_content_signature, sign_tx
    from trezor.messages import BinanceCancelMsg
    from trezor.messages import BinanceCoin
    from trezor.messages import BinanceInputOutput
    from trezor.messages import BinanceOrderMsg
    from trezor.messages import BinanceSignTx
    from trezor.messages import BinanceTransferMsg


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestBinanceSign(unittest.TestCase):
    def test_order_signature(self):
        # source of testing data
        # https://github.com/binance-chain/javascript-sdk/blob/master/__tests__/fixtures/placeOrder.json
        json_msg = '{"account_number":"34","chain_id":"Binance-Chain-Nile","data":null,"memo":"","msgs":[{"id":"BA36F0FAD74D8F41045463E4774F328F4AF779E5-33","ordertype":2,"price":100000000,"quantity":100000000,"sender":"tbnb1hgm0p7khfk85zpz5v0j8wnej3a90w709zzlffd","side":1,"symbol":"ADA.B-B63_BNB","timeinforce":1}],"sequence":"32","source":"1"}'
        expected_signature = "851fc9542342321af63ecbba7d3ece545f2a42bad01ba32cff5535b18e54b6d3106e10b6a4525993d185a1443d9a125186960e028eabfdd8d76cf70a3a7e3100"
        public_key = "029729a52e4e3c2b4a4e52aa74033eedaf8ba1df5ab6d1f518fd69e67bbd309b0e"
        private_key = "90335b9d2153ad1a9799a3ccc070bd64b4164e9642ee1dd48053c33f9a3a05e9"

        # Testing data for object creation is decoded from json_msg
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

        # check if our json string produced for signing is the same as test vector
        self.assertEqual(msg_json, json_msg)

        # verify signature against public key
        signature = generate_content_signature(msg_json.encode(), unhexlify(private_key))
        self.assertTrue(verify_content_signature(unhexlify(public_key), signature, json_msg))

        # check if the signed data is the same as test vector
        self.assertEqual(signature, unhexlify(expected_signature))

    def test_cancel_signature(self):
        # source of testing data
        # https://github.com/binance-chain/javascript-sdk/blob/master/__tests__/fixtures/cancelOrder.json
        json_msg = '{"account_number":"34","chain_id":"Binance-Chain-Nile","data":null,"memo":"","msgs":[{"refid":"BA36F0FAD74D8F41045463E4774F328F4AF779E5-29","sender":"tbnb1hgm0p7khfk85zpz5v0j8wnej3a90w709zzlffd","symbol":"BCHSV.B-10F_BNB"}],"sequence":"33","source":"1"}'
        expected_signature = "d93fb0402b2b30e7ea08e123bb139ad68bf0a1577f38592eb22d11e127f09bbd3380f29b4bf15bdfa973454c5c8ed444f2e256e956fe98cfd21e886a946e21e5"
        public_key = "029729a52e4e3c2b4a4e52aa74033eedaf8ba1df5ab6d1f518fd69e67bbd309b0e"
        private_key = "90335b9d2153ad1a9799a3ccc070bd64b4164e9642ee1dd48053c33f9a3a05e9"

        # Testing data for object creation is decoded from json_msg
        envelope = BinanceSignTx(msg_count=1, account_number=34, chain_id="Binance-Chain-Nile", memo="", sequence=33, source=1)
        msg = BinanceCancelMsg(refid="BA36F0FAD74D8F41045463E4774F328F4AF779E5-29",
                               sender="tbnb1hgm0p7khfk85zpz5v0j8wnej3a90w709zzlffd",
                               symbol="BCHSV.B-10F_BNB")

        msg_json = produce_json_for_signing(envelope, msg)

        # check if our json string produced for signing is the same as test vector
        self.assertEqual(msg_json, json_msg)

        # verify signature against public key
        signature = generate_content_signature(msg_json.encode(), unhexlify(private_key))
        self.assertTrue(verify_content_signature(unhexlify(public_key), signature, json_msg))

        #check if the signed data is the same as test vector
        self.assertEqual(signature, unhexlify(expected_signature))

    def test_transfer_signature(self):
        # source of testing data
        # https://github.com/binance-chain/javascript-sdk/blob/master/__tests__/fixtures/transfer.json
        json_msg = '{"account_number":"34","chain_id":"Binance-Chain-Nile","data":null,"memo":"test","msgs":[{"inputs":[{"address":"tbnb1hgm0p7khfk85zpz5v0j8wnej3a90w709zzlffd","coins":[{"amount":1000000000,"denom":"BNB"}]}],"outputs":[{"address":"tbnb1ss57e8sa7xnwq030k2ctr775uac9gjzglqhvpy","coins":[{"amount":1000000000,"denom":"BNB"}]}]}],"sequence":"31","source":"1"}'
        expected_signature = "faf5b908d6c4ec0c7e2e7d8f7e1b9ca56ac8b1a22b01655813c62ce89bf84a4c7b14f58ce51e85d64c13f47e67d6a9187b8f79f09e0a9b82019f47ae190a4db3"
        public_key = "029729a52e4e3c2b4a4e52aa74033eedaf8ba1df5ab6d1f518fd69e67bbd309b0e"
        private_key = "90335b9d2153ad1a9799a3ccc070bd64b4164e9642ee1dd48053c33f9a3a05e9"

        # Testing data for object creation is decoded from json_msg
        envelope = BinanceSignTx(msg_count=1, account_number=34, chain_id="Binance-Chain-Nile", memo="test", sequence=31, source=1)
        coin = BinanceCoin(denom="BNB", amount=1000000000)
        first_input = BinanceInputOutput(address="tbnb1hgm0p7khfk85zpz5v0j8wnej3a90w709zzlffd", coins=[coin])
        first_output = BinanceInputOutput(address="tbnb1ss57e8sa7xnwq030k2ctr775uac9gjzglqhvpy", coins=[coin])
        msg = BinanceTransferMsg(inputs=[first_input], outputs=[first_output])

        msg_json = produce_json_for_signing(envelope, msg)

        # check if our json string produced for signing is the same as test vector
        self.assertEqual(msg_json, json_msg)

        # verify signature against public key
        signature = generate_content_signature(msg_json.encode(), unhexlify(private_key))
        self.assertTrue(verify_content_signature(unhexlify(public_key), signature, json_msg))

        # check if the signed data is the same as test vector
        self.assertEqual(signature, unhexlify(expected_signature))

def verify_content_signature(
    public_key: bytes, signature: bytes, unsigned_data: bytes
) -> bool:
    msghash = sha256(unsigned_data).digest()
    return secp256k1.verify(public_key, signature, msghash)

if __name__ == '__main__':
    unittest.main()
