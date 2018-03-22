from common import *

from apps.nem.transaction import *
from trezor.crypto import hashlib


class TestNemTransactionMosaicCreation(unittest.TestCase):

    def test_nem_transaction_mosaic_creation(self):

        t = nem_transaction_create_mosaic_creation(NEM_NETWORK_TESTNET,
                                                       14070896,
                                                       unhexlify('994793ba1c789fa9bdea918afc9b06e2d0309beb1081ac5b6952991e4defd324'),
                                                       108000000,
                                                       14074496,
                                                       'gimre.games.pong',
                                                       'paddles',
                                                       'Paddles for the bong game.\n',
                                                       0,
                                                       10000,
                                                       True,
                                                       True,
                                                       0,
                                                       0,
                                                       '',
                                                       '',
                                                       '',
                                                       'TBMOSAICOD4F54EE5CDMR23CCBGOAM2XSJBR5OLC',
                                                       50000000000)

        self.assertEqual(t, unhexlify('014000000100009870b4d60020000000994793ba1c789fa9bdea918afc9b06e2d0309beb1081ac5b6952991e4defd32400f36f060000000080c2d600de00000020000000994793ba1c789fa9bdea918afc9b06e2d0309beb1081ac5b6952991e4defd3241f0000001000000067696d72652e67616d65732e706f6e6707000000706164646c65731b000000506164646c657320666f722074686520626f6e672067616d652e0a04000000150000000c00000064697669736962696c69747901000000301a0000000d000000696e697469616c537570706c79050000003130303030190000000d000000737570706c794d757461626c650400000074727565180000000c0000007472616e7366657261626c650400000074727565000000002800000054424d4f534149434f443446353445453543444d523233434342474f414d3258534a4252354f4c4300743ba40b000000'))
        self.assertEqual(hashlib.sha3_256(t).digest(True), unhexlify('68364353c29105e6d361ad1a42abbccbf419cfc7adb8b74c8f35d8f8bdaca3fa'))

    
if __name__ == '__main__':
    unittest.main()
