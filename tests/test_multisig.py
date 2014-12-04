import unittest
import common
import binascii
import itertools

import trezorlib.messages_pb2 as proto
import trezorlib.types_pb2 as proto_types
from trezorlib.client import CallException
from trezorlib.tx_api import TXAPITestnet, TXAPIBitcoin

# Multisig howto:
#
# https://sx.dyne.org/multisig.html
#

class TestMultisig(common.TrezorTest):
    def test_first_sig(self):
        self.setup_mnemonic_nopin_nopassphrase()

        #key1 = self.client.get_public_node([1])
        #key2 = self.client.get_public_node([2])
        #key3 = self.client.get_public_node([3])

        # pubkeys:
        #    0338d78612e990f2eea0c426b5e48a8db70b9d7ed66282b3b26511e0b1c75515a6
        #    038caebd6f753bbbd2bb1f3346a43cd32140648583673a31d62f2dfb56ad0ab9e3
        #    03477b9f0f34ae85434ce795f0c5e1e90c9420e5b5fad084d7cce9a487b94a7902

        # redeem script:
        # 52210338d78612e990f2eea0c426b5e48a8db70b9d7ed66282b3b26511e0b1c75515a621038caebd6f753bbbd2bb1f3346a43cd32140648583673a31d62f2dfb56ad0ab9e32103477b9f0f34ae85434ce795f0c5e1e90c9420e5b5fad084d7cce9a487b94a790253ae

        # multisig address: 3E7GDtuHqnqPmDgwH59pVC7AvySiSkbibz

        # tx: c6091adf4c0c23982a35899a6e58ae11e703eacd7954f588ed4b9cdefc4dba52
        # input 1: 0.001 BTC

        multisig = proto_types.MultisigRedeemScriptType(
                            pubkeys=[binascii.unhexlify('0338d78612e990f2eea0c426b5e48a8db70b9d7ed66282b3b26511e0b1c75515a6'),
                                     binascii.unhexlify('038caebd6f753bbbd2bb1f3346a43cd32140648583673a31d62f2dfb56ad0ab9e3'),
                                     binascii.unhexlify('03477b9f0f34ae85434ce795f0c5e1e90c9420e5b5fad084d7cce9a487b94a7902')],
                            signatures=['', '', ''],
                            m=2,
                            )

        # Let's go to sign with key 1
        inp1 = proto_types.TxInputType(address_n=[1],
                             prev_hash=binascii.unhexlify('c6091adf4c0c23982a35899a6e58ae11e703eacd7954f588ed4b9cdefc4dba52'),
                             prev_index=1,
                             script_type=proto_types.SPENDMULTISIG,
                             multisig=multisig,
                             )
        
        out1 = proto_types.TxOutputType(address='12iyMbUb4R2K3gre4dHSrbu5azG5KaqVss',
                              amount=100000,
                              script_type=proto_types.PAYTOADDRESS)

        with self.client:
            self.client.set_expected_responses([
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXMETA, details=proto_types.TxRequestDetailsType(tx_hash=binascii.unhexlify("c6091adf4c0c23982a35899a6e58ae11e703eacd7954f588ed4b9cdefc4dba52"))),
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0, tx_hash=binascii.unhexlify("c6091adf4c0c23982a35899a6e58ae11e703eacd7954f588ed4b9cdefc4dba52"))),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=0, tx_hash=binascii.unhexlify("c6091adf4c0c23982a35899a6e58ae11e703eacd7954f588ed4b9cdefc4dba52"))),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=1, tx_hash=binascii.unhexlify("c6091adf4c0c23982a35899a6e58ae11e703eacd7954f588ed4b9cdefc4dba52"))),                
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.ButtonRequest(code=proto_types.ButtonRequest_ConfirmOutput),
                proto.ButtonRequest(code=proto_types.ButtonRequest_SignTx),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXFINISHED),
            ])
            
            # Now we have first signature
            (signatures1, _) = self.client.sign_tx('Bitcoin', [inp1, ], [out1, ])

        # ---------------------------------------
        # Let's do second signature using 3rd key
        
        multisig = proto_types.MultisigRedeemScriptType(
                            pubkeys=[binascii.unhexlify('0338d78612e990f2eea0c426b5e48a8db70b9d7ed66282b3b26511e0b1c75515a6'),
                                     binascii.unhexlify('038caebd6f753bbbd2bb1f3346a43cd32140648583673a31d62f2dfb56ad0ab9e3'),
                                     binascii.unhexlify('03477b9f0f34ae85434ce795f0c5e1e90c9420e5b5fad084d7cce9a487b94a7902')],
                            signatures=[signatures1[0], '', ''], # Fill signature from previous signing process
                            m=2,
                            )
        
        # Let's do a second signature with key 3
        inp3 = proto_types.TxInputType(address_n=[3],
                 prev_hash=binascii.unhexlify('c6091adf4c0c23982a35899a6e58ae11e703eacd7954f588ed4b9cdefc4dba52'),
                 prev_index=1,
                 script_type=proto_types.SPENDMULTISIG,
                 multisig=multisig,
                 )

        with self.client:
            self.client.set_expected_responses([
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXMETA, details=proto_types.TxRequestDetailsType(tx_hash=binascii.unhexlify("c6091adf4c0c23982a35899a6e58ae11e703eacd7954f588ed4b9cdefc4dba52"))),
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0, tx_hash=binascii.unhexlify("c6091adf4c0c23982a35899a6e58ae11e703eacd7954f588ed4b9cdefc4dba52"))),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=0, tx_hash=binascii.unhexlify("c6091adf4c0c23982a35899a6e58ae11e703eacd7954f588ed4b9cdefc4dba52"))),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=1, tx_hash=binascii.unhexlify("c6091adf4c0c23982a35899a6e58ae11e703eacd7954f588ed4b9cdefc4dba52"))),                
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.ButtonRequest(code=proto_types.ButtonRequest_ConfirmOutput),
                proto.ButtonRequest(code=proto_types.ButtonRequest_SignTx),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXFINISHED),
            ])
            (signatures2, serialized_tx) = self.client.sign_tx('Bitcoin', [inp3, ], [out1, ])

        # Accepted by network: tx 
        self.assertEqual(binascii.hexlify(serialized_tx), '010000000152ba4dfcde9c4bed88f55479cdea03e711ae586e9a89352a98230c4cdf1a09c601000000fdfe0000483045022100985cc1ba316d140eb4b2d4028d8cd1c451f87bff8ff679858732e516ad04cd3402207af6edda99972af0baa7702a3b7448517c8242e7bca669f6861771cdd16ee05801483045022100f5428fe0531b3095675b40d87cab607ee036fac823b22e8dcec35b65aff6e52b022032129b4577ff923d321a1c70db5a6cec5bcc142cb2c51901af8b989cced23e0d014c6952210338d78612e990f2eea0c426b5e48a8db70b9d7ed66282b3b26511e0b1c75515a621038caebd6f753bbbd2bb1f3346a43cd32140648583673a31d62f2dfb56ad0ab9e32103477b9f0f34ae85434ce795f0c5e1e90c9420e5b5fad084d7cce9a487b94a790253aeffffffff01a0860100000000001976a91412e8391ad256dcdc023365978418d658dfecba1c88ac00000000')

if __name__ == '__main__':
    unittest.main()
