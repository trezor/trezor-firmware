# tx 4a7b7e0403ae5607e473949cfa03f09f2cd8b0f404bf99ce10b7303d86280bf7
# 100 UTXO for spending for unittests

import unittest
import common
import binascii

import trezorlib.messages_pb2 as proto
import trezorlib.types_pb2 as proto_types
from trezorlib.client import CallException
from trezorlib.tx_api import TXAPITestnet, TXAPIBitcoin

class TestMsgSigntx(common.TrezorTest):
    def test_two_two(self):
        self.setup_mnemonic_nopin_nopassphrase()

        # tx: c6be22d34946593bcad1d2b013e12f74159e69574ffea21581dad115572e031c
        # input 1: 0.0010 BTC
        # tx: 58497a7757224d1ff1941488d23087071103e5bf855f4c1c44e5c8d9d82ca46e
        # input 1: 0.0011 BTC

        inp1 = proto_types.TxInputType(address_n=[1],  # 1CK7SJdcb8z9HuvVft3D91HLpLC6KSsGb
                             # amount=100000,
                             prev_hash=binascii.unhexlify('c6be22d34946593bcad1d2b013e12f74159e69574ffea21581dad115572e031c'),
                             prev_index=1,
                             )

        inp2 = proto_types.TxInputType(address_n=[2],  # 15AeAhtNJNKyowK8qPHwgpXkhsokzLtUpG
                             # amount=110000,
                             prev_hash=binascii.unhexlify('58497a7757224d1ff1941488d23087071103e5bf855f4c1c44e5c8d9d82ca46e'),
                             prev_index=1,
                             )

        out1 = proto_types.TxOutputType(address='15Jvu3nZNP7u2ipw2533Q9VVgEu2Lu9F2B',
                              amount=210000 - 100000 - 10000,
                              script_type=proto_types.PAYTOADDRESS,
                              )

        out2 = proto_types.TxOutputType(address_n=[3],  # 1CmzyJp9w3NafXMSEFH4SLYUPAVCSUrrJ5
                              amount=100000,
                              script_type=proto_types.PAYTOADDRESS,
                              )

        with self.client:
            # self.client.set_expected_responses([proto.ButtonRequest(code=proto_types.ButtonRequest_ConfirmOutput),
            #                                    # proto.ButtonRequest(code=proto_types.ButtonRequest_ConfirmOutput), # don't confirm change
            #                                    proto.ButtonRequest(code=proto_types.ButtonRequest_SignTx),
            #                                    proto.TxRequest(finished=True)])
            (signatures, serialized_tx) = self.client.sign_tx('Bitcoin', [inp1, inp2], [out1, out2])

        # Accepted by network: tx c63e24ed820c5851b60c54613fbc4bcb37df6cd49b4c96143e99580a472f79fb
        self.assertEqual(binascii.hexlify(serialized_tx), '01000000021c032e5715d1da8115a2fe4f57699e15742fe113b0d2d1ca3b594649d322bec6010000006b483045022100f773c403b2f85a5c1d6c9c4ad69c43de66930fff4b1bc818eb257af98305546a0220443bde4be439f276a6ce793664b463580e210ec6c9255d68354449ac0443c76501210338d78612e990f2eea0c426b5e48a8db70b9d7ed66282b3b26511e0b1c75515a6ffffffff6ea42cd8d9c8e5441c4c5f85bfe50311078730d2881494f11f4d2257777a4958010000006b48304502210090cff1c1911e771605358a8cddd5ae94c7b60cc96e50275908d9bf9d6367c79f02202bfa72e10260a146abd59d0526e1335bacfbb2b4401780e9e3a7441b0480c8da0121038caebd6f753bbbd2bb1f3346a43cd32140648583673a31d62f2dfb56ad0ab9e3ffffffff02a0860100000000001976a9142f4490d5263906e4887ca2996b9e207af3e7824088aca0860100000000001976a914812c13d97f9159e54e326b481b8f88a73df8507a88ac00000000')


'''
    def test_signtx(self):
        expected_tx = '01000000012de70f7d6ffed0db70f8882f3fca90db9bb09f0e99bce27468c23d3c994fcd56' \
            '010000008b4830450221009b985e14d53cfeed3496846db6ddaa77a0206138d0df4c2ccd3b' \
            '759e91bae3e1022004c76e10f99ccac8ced761719181a96bae25a74829eab3ecb8f29eb07f' \
            'e18f7e01410436ae8595f03a7324d1d1482ede8560a4508c767fbc662559482d5759b32209' \
            'a62964699995f6e018cfbeb7a71a66d4c64fa38875d79ead0a9ac66f59c1c8b3a3ffffffff' \
            '0250c30000000000001976a91444ce5c6789b0bb0e8a9ab9a4769fe181cb274c4688aca086' \
            '0100000000001976a9149e03078026388661b197129a43f0f64f88379ce688ac00000000'

        inp1 = proto.TxInput(index=0,
                             address_n=[1, 0],
                             amount=200000, # 0.002 BTC
                             prev_hash=binascii.unhexlify('56cd4f993c3dc26874e2bc990e9fb09bdb90ca3f2f88f870dbd0fe6f7d0fe72d'),
                             prev_index=1,
                             #script_sig=
                             )      

        out1 = proto.TxOutput(index=0,
                              address='1GnnT11aZeH6QZCtT7EjCvRF3EXHoY3owE',
                              address_n=[0, 1],
                              amount=50000, # 0.0005 BTC
                              script_type=proto.PAYTOADDRESS,
                              #script_args=
                              )        
                   
        out2 = proto.TxOutput(index=1,
                              address='1FQVPnjrbkPWeA8poUoEnX9U3n9DyhAVtv',
                              #address_n=[],
                              amount=100000, # 0.001 BTC
                              script_type=proto.PAYTOADDRESS,
                              #script_args=
                              )

        print binascii.hexlify(self.client.sign_tx([inp1], [out1, out2])[1])

    def test_workflow(self):
        inp1 = proto.TxInput(index=0,
                             address_n=[1,0],
                             amount=100000000,
                             prev_hash='prevhash1234354346543456543654',
                             prev_index=11,
                             )      

        inp2 = proto.TxInput(index=1,
                             address_n=[2,0],
                             amount=100000000,
                             prev_hash='prevhash2222254346543456543654',
                             prev_index=11,
                             )      
                   
        out1 = proto.TxOutput(index=0,
                              address='1BitkeyP2nDd5oa647AjvBbbwST54W5Zmx',
                              amount=100000000,
                              script_type=proto.PAYTOADDRESS,
                              )

        out2 = proto.TxOutput(index=1,
                              address='1BitkeyP2nDd5oa647AjvBbbwST54W5Zmx',
                              #address_n=[],
                              amount=100000000,
                              script_type=proto.PAYTOADDRESS,
                              #script_args=
                              )

        serialized = ''
                
        # Prepare and send initial message
        tx = proto.SignTx()
        tx.algo = proto.ELECTRUM
        tx.random = self.client._get_local_entropy()
        tx.inputs_count = 2
        tx.outputs_count = 2            

        res = self.client.call(tx)
        self.assertIsInstance(res, proto.TxRequest)
        self.assertEqual(res.request_type, proto.TXINPUT)
        self.assertEqual(res.request_index, 0)
        self.assertEqual(res.signature, '')
        self.assertEqual(res.serialized_tx, '')
        
        # FIRST SIGNATURE
        res = self.client.call(inp1)
        self.assertIsInstance(res, proto.TxRequest)
        self.assertEqual(res.request_type, proto.TXINPUT)
        self.assertEqual(res.request_index, 1)
        self.assertEqual(res.signature, '')
        self.assertEqual(res.serialized_tx, '')
        
        res = self.client.call(inp2)
        self.assertIsInstance(res, proto.TxRequest)
        self.assertEqual(res.request_type, proto.TXOUTPUT)
        self.assertEqual(res.request_index, 0)
        self.assertEqual(res.signature, '')
        self.assertEqual(res.serialized_tx, '')

        res = self.client.call(out1)
        self.assertIsInstance(res, proto.TxRequest)
        self.assertEqual(res.request_type, proto.TXOUTPUT)
        self.assertEqual(res.request_index, 1)
        self.assertEqual(res.signature, '')
        self.assertEqual(res.serialized_tx, '')

        res = self.client.call(out2)
        self.assertIsInstance(res, proto.TxRequest)
        self.assertEqual(res.request_type, proto.TXINPUT)
        self.assertEqual(res.request_index, 0)
        self.assertNotEqual(res.signature, '')
        self.assertNotEqual(res.serialized_tx, '')
        serialized += res.serialized_tx
        
        # SECOND SIGNATURE
        res = self.client.call(inp1)
        self.assertIsInstance(res, proto.TxRequest)
        self.assertEqual(res.request_type, proto.TXINPUT)
        self.assertEqual(res.request_index, 1)
        self.assertEqual(res.signature, '')
        self.assertEqual(res.serialized_tx, '')
        
        res = self.client.call(inp2)
        self.assertIsInstance(res, proto.TxRequest)
        self.assertEqual(res.request_type, proto.TXOUTPUT)
        self.assertEqual(res.request_index, 0)
        self.assertEqual(res.signature, '')
        self.assertEqual(res.serialized_tx, '')

        res = self.client.call(out1)
        self.assertIsInstance(res, proto.TxRequest)
        self.assertEqual(res.request_type, proto.TXOUTPUT)
        self.assertEqual(res.request_index, 1)
        self.assertEqual(res.signature, '')
        self.assertEqual(res.serialized_tx, '')

        res = self.client.call(out2)
        self.assertIsInstance(res, proto.TxRequest)
        self.assertEqual(res.request_type, proto.TXOUTPUT)
        self.assertEqual(res.request_index, 0)
        self.assertNotEqual(res.signature, '')
        self.assertNotEqual(res.serialized_tx, '')
        serialized += res.serialized_tx
        
        # FINALIZING OUTPUTS
        res = self.client.call(out1)
        self.assertIsInstance(res, proto.TxRequest)
        self.assertEqual(res.request_type, proto.TXOUTPUT)
        self.assertEqual(res.request_index, 1)
        self.assertEqual(res.signature, '')
        self.assertNotEqual(res.serialized_tx, '')
        serialized += res.serialized_tx
        
        res = self.client.call(out2)
        self.assertIsInstance(res, proto.TxRequest)
        self.assertEqual(res.request_type, proto.TXOUTPUT)
        self.assertEqual(res.request_index, -1)
        self.assertEqual(res.signature, '')
        self.assertNotEqual(res.serialized_tx, '')
        serialized += res.serialized_tx
        
        print binascii.hexlify(serialized)
'''

if __name__ == '__main__':
    unittest.main()
