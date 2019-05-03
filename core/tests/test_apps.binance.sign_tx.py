from common import *

from trezor.crypto.curve import secp256k1

from apps.binance.helpers import produce_json_for_signing
from apps.binance.sign_tx import generate_content_signature, verify_content_signature
from trezor.messages.BinanceOrderMsg import BinanceOrderMsg
from trezor.messages.BinanceSignTx import BinanceSignTx


class TestBinanceSign(unittest.TestCase):
    def testTransactionSignature(self):
        # Testing data from binance sdk
        json_hex_msg = "7b226163636f756e745f6e756d626572223a2231222c22636861696e5f6964223a22626e62636861696e2d31303030222c226d656d6f223a22222c226d736773223a5b7b226964223a22423635363144434331303431333030353941374330384634384336343631304331463646393036342d3130222c226f7264657274797065223a322c227072696365223a3130303030303030302c227175616e74697479223a313230303030303030302c2273656e646572223a22626e63316b6574706d6e71736779637174786e7570723667636572707073306b6c797279687a36667a6c222c2273696465223a312c2273796d626f6c223a224254432d3543345f424e42222c2274696d65696e666f726365223a317d5d2c2273657175656e6365223a2239227d"
        expected_result = "9c0421217ef92d556a14e3f442b07c85f6fc706dfcd8a72d6b58f05f96e95aa226b10f7cf62ccf7c9d5d953fa2c9ae80a1eacaf0c779d0253f1a34afd17eef34"
        private_key = "30c5e838578a29e3e9273edddd753d6c9b38aca2446dd84bdfe2e5988b0da0a1"

        # Testing data for object creation is decoded from json_hex_msg
        envelope = BinanceSignTx(account_number=1, chain_id="bnbchain-1000", memo="", sequence=9)
        msg = BinanceOrderMsg(id="B6561DCC104130059A7C08F48C64610C1F6F9064-10", ordertype=2, price=100000000, quantity=1200000000,
                                     sender="bnc1ketpmnqsgycqtxnupr6gcerpps0klyryhz6fzl", side=1, symbol="BTC-5C4_BNB", timeinforce=1)

        msg_json = produce_json_for_signing(envelope, msg)
        
        #check if our json string produced for signing is the same as test vector
        self.assertEqual(hexlify(msg_json).decode(), json_hex_msg)
        
        signature = generate_content_signature(msg_json.encode(), unhexlify(private_key))

        #verify signature against public key
        pubkey = secp256k1.publickey(unhexlify(private_key))
        self.assertTrue(verify_content_signature(pubkey, signature, unhexlify(json_hex_msg)))

        #check if the signed data is the same as test vector
        #TODO: !!!figure out where the extra byte comes from!!!
        self.assertEqual(signature[1:65], unhexlify(expected_result))

if __name__ == '__main__':
    unittest.main()
