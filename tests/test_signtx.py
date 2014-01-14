import unittest
import common
import binascii

import trezorlib.messages_pb2 as proto
import trezorlib.types_pb2 as proto_types

class TestSignTx(common.TrezorTest):

    '''
    def test_simplesigntx(self):
        # tx: d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882
        # input 0: 0.0039 BTC

        inp1 = proto_types.TxInputType(address_n=[0],  # 14LmW5k4ssUrtbAB4255zdqv3b4w1TuX9e
                             # amount=390000,
                             prev_hash=binascii.unhexlify('d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882'),
                             prev_index=0,
                             )

        out1 = proto_types.TxOutputType(address='1MJ2tj2ThBE62zXbBYA5ZaN3fdve5CPAz1',
                              amount=380000,
                              script_type=proto_types.PAYTOADDRESS,
                              )

        tx = self.client.simple_sign_tx('Bitcoin', [inp1, ], [out1, ])
        print binascii.hexlify(tx.serialized_tx)
        self.assertEqual(binascii.hexlify(tx.serialized_tx), '010000000182488650ef25a58fef6788bd71b8212038d7f2bbe4750bc7bcb44701e85ef6d5000000006b4830450221009a0b7be0d4ed3146ee262b42202841834698bb3ee39c24e7437df208b8b7077102202b79ab1e7736219387dffe8d615bbdba87e11477104b867ef47afed1a5ede7810121023230848585885f63803a0a8aecdd6538792d5c539215c91698e315bf0253b43dffffffff0160cc0500000000001976a914de9b2a8da088824e8fe51debea566617d851537888ac00000000')
    '''


    def test_simplesigntx_testnet(self):
        # tx: d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882
        # input 0: 0.0039 BTC
        self.client.load_device_by_xprv('xprv9s21ZrQH143K3zttRjiQmYwyugvd13pnd2VzefWrfSouRfnj5oSkJgBQXxtn18E9mqrDop7fQ8Xnb9JCLPE4vghzhpU4dT33ZJ7frjzTEW8',
                                        '', False, 'testnet')

        inp1 = proto_types.TxInputType(address_n=[6],  # mo8uUSFJULCMA4neRS9aS9jiXZ1N72FSLK
                             # amount=390000,
                             prev_hash=binascii.unhexlify('d83b27f16ce5069e0c8e4a02813f252500e257744d5b00c9b6128be7189117b1'),
                             prev_index=0,
                             )

        out1 = proto_types.TxOutputType(address='mjKKH3Dk95VMbdNnDQYHZXoQ9QwuCZocwb',
                              amount=80085000,
                              script_type=proto_types.PAYTOADDRESS,
                              )

        rawtx = {'d83b27f16ce5069e0c8e4a02813f252500e257744d5b00c9b6128be7189117b1': '01000000013b21cc65080c57793d0e47045a24d8e92262dc47efdc425fd5cad9a25e928f6c000000006b483045022100bde591f2c997bafa8388916663b148f4093914851a33a9903da69ad97afa6f470220138c6ff11321339974bac9c0992d7b9d72aef0c2d098f26267ec9f05d532c859012103edcc8dc5cac7dca6ed191d812621fb300863fea0dd5d14180b482b917a35acc4ffffffff020800c604000000001976a91453958011070469e2ef5e1115f34f509717d6884288acf8c99502000000001976a9141e2ba9407a6920246d0f345beecb89ed47c99a7788ac00000000'}
        tx = self.client.simple_sign_tx('Testnet', [inp1, ], [out1, ])
        print binascii.hexlify(tx.serialized_tx)
        # self.assertEqual(binascii.hexlify(tx.serialized_tx), '010000000182488650ef25a58fef6788bd71b8212038d7f2bbe4750bc7bcb44701e85ef6d5000000006b4830450221009a0b7be0d4ed3146ee262b42202841834698bb3ee39c24e7437df208b8b7077102202b79ab1e7736219387dffe8d615bbdba87e11477104b867ef47afed1a5ede7810121023230848585885f63803a0a8aecdd6538792d5c539215c91698e315bf0253b43dffffffff0160cc0500000000001976a914de9b2a8da088824e8fe51debea566617d851537888ac00000000')


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
    '''
    '''    
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
