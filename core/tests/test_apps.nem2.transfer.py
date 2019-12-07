from common import *

from trezor.crypto import hashlib

if not utils.BITCOIN_ONLY:
    from apps.nem2.helpers import *
    from apps.nem2.mosaic import *
    from apps.nem2.transfer import *
    from apps.nem2.transfer.serialize import *
    from trezor.messages.NEM2TransferTransaction import NEM2TransferTransaction
    from trezor.messages.NEM2SignTx import NEM2SignTx
    from trezor.messages.NEM2Mosaic import NEM2Mosaic
    from trezor.messages.NEM2TransferMessage import NEM2TransferMessage
    from trezor.messages.NEM2Address import NEM2Address


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestNem2Transfer(unittest.TestCase):

    def test_create_transfer(self):

        transaction = NEM2TransactionCommon(
            network_type=NEM2_NETWORK_TEST_NET,
            type=NEM2_TRANSACTION_TYPE_TRANSFER,
            version=38913,
            max_fee="20000",
            deadline="113248176649"
        )

        transfer = NEM2TransferTransaction(
            recipient_address=NEM2Address(
                address="TAO6QEUC3APBTMDAETMG6IZJI7YOXWHLGC5T4HA4",
                network_type=NEM2_NETWORK_TEST_NET
            ),
            message=NEM2TransferMessage(
                payload="",
                type=0
            ),
            mosaics=[NEM2Mosaic(id="308F144790CD7BC4", amount=1000000000)]
        )

        t = serialize_transfer(transaction, transfer)

        self.assertEqual(t, unhexlify('B1000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001985441204E000000000000090A1E5E1A000000981DE81282D81E19B06024D86F232947F0EBD8EB30BB3E1C1C01010000000000C47BCD9047148F3000CA9A3B0000000000'))
        # self.assertEqual(hashlib.sha3_256(t, keccak=True).digest(), unhexlify('0acbf8df91e6a65dc56c56c43d65f31ff2a6a48d06fc66e78c7f3436faf3e74f'))

    def test_create_transfer_with_message_payload(self):


        transaction = NEM2TransactionCommon(
            network_type=NEM2_NETWORK_TEST_NET,
            type=NEM2_TRANSACTION_TYPE_TRANSFER,
            version=38913,
            max_fee="20000",
            deadline="113248176649"
        )

        transfer = NEM2TransferTransaction(
            recipient_address=NEM2Address(
                address="TAO6QEUC3APBTMDAETMG6IZJI7YOXWHLGC5T4HA4",
                network_type=NEM2_NETWORK_TEST_NET
            ),
            message=NEM2TransferMessage(
                payload="Test Transfer",
                type=0
            ),
            mosaics=[NEM2Mosaic(id="308F144790CD7BC4", amount=1000000000)]
        )

        t = serialize_transfer(transaction, transfer)

        self.assertEqual(t, unhexlify('BE000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001985441204E000000000000090A1E5E1A000000981DE81282D81E19B06024D86F232947F0EBD8EB30BB3E1C1C010E0000000000C47BCD9047148F3000CA9A3B000000000054657374205472616E73666572'))
        # self.assertEqual(hashlib.sha3_256(t, keccak=True).digest(), unhexlify('923EB29CF8C75E9BB03DB064C47389FD98B1EC2A62CD7C685FBA7F706B09DF73'))

if __name__ == '__main__':
    unittest.main()