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
