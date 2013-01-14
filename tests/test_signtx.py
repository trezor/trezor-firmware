import unittest
import common

import bitkeylib.bitkey_pb2 as proto

class TestSignTx(common.BitkeyTest):
    def test_signtx(self):
        inp1 = proto.TxInput(index=0,
                             address_n=[1,],
                             amount=100000000,
                             prev_hash='prevhash1234354346543456543654',
                             prev_index=11,
                             #script_sig=
                             )      

        inp2 = proto.TxInput(index=1,
                             address_n=[2,],
                             amount=100000000,
                             prev_hash='prevhash2222254346543456543654',
                             prev_index=11,
                             #script_sig=
                             )      
                   
        out1 = proto.TxOutput(index=0,
                              address='1Bitkey',
                              #address_n=[],
                              amount=100000000,
                              script_type=proto.PAYTOADDRESS,
                              #script_args=
                              )

        out2 = proto.TxOutput(index=1,
                              address='1Bitkey2',
                              #address_n=[],
                              amount=100000000,
                              script_type=proto.PAYTOADDRESS,
                              #script_args=
                              )
        
        print self.bitkey.sign_tx([inp1, inp2], [out1, out2])
        
if __name__ == '__main__':
    unittest.main()