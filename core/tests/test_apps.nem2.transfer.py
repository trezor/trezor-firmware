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
    from trezor.messages.NEM2RecipientAddress import NEM2RecipientAddress


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestNem2Transfer(unittest.TestCase):

    def test_create_transfer(self):

        # http://api-01.mt.us-west-2.nemtech.network:3000/transaction/8729BE2004B61CFFCEC2B7264DAF48A0F7E952258269C176BB678C385366E373
        m = _create_msg(NEM2_NETWORK_TEST_NET,
                        NEM2_TRANSACTION_TYPE_TRANSFER,
                        38913,
                        "20000",
                        "113248176649",
                        {
                            "address": "TAO6QEUC3APBTMDAETMG6IZJI7YOXWHLGC5T4HA4",
                            "network_type": NEM2_NETWORK_TEST_NET
                        },
                        {"payload": "", "type": 0},
                        [{ "id": "308F144790CD7BC4", "amount": 1000000000}]
                    )

        t = serialize_transfer(m.transaction, m.transfer)

        self.assertEqual(t, unhexlify('B1000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001985441204E000000000000090A1E5E1A000000981DE81282D81E19B06024D86F232947F0EBD8EB30BB3E1C1C01010000000000C47BCD9047148F3000CA9A3B0000000000'))
        # self.assertEqual(hashlib.sha3_256(t, keccak=True).digest(), unhexlify('0acbf8df91e6a65dc56c56c43d65f31ff2a6a48d06fc66e78c7f3436faf3e74f'))

    def test_create_transfer_with_message_payload(self):

        m = _create_msg(NEM2_NETWORK_TEST_NET,
                        NEM2_TRANSACTION_TYPE_TRANSFER,
                        38913,
                        "20000",
                        "113248176649",
                        {
                            "address": "TAO6QEUC3APBTMDAETMG6IZJI7YOXWHLGC5T4HA4",
                            "network_type": NEM2_NETWORK_TEST_NET
                        },
                        {"payload": "Test Transfer", "type": 0},
                        [{ "id": "308F144790CD7BC4", "amount": 1000000000}]
                    )

        t = serialize_transfer(m.transaction, m.transfer)

        self.assertEqual(t, unhexlify('BE000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001985441204E000000000000090A1E5E1A000000981DE81282D81E19B06024D86F232947F0EBD8EB30BB3E1C1C010E0000000000C47BCD9047148F3000CA9A3B000000000054657374205472616E73666572'))
        # self.assertEqual(hashlib.sha3_256(t, keccak=True).digest(), unhexlify('923EB29CF8C75E9BB03DB064C47389FD98B1EC2A62CD7C685FBA7F706B09DF73'))

def _create_msg(network_type: int, tx_type: int, version: int, max_fee: str,
                deadline: str, recipient_address: dict, message: dict, mosaics: list):
    m = NEM2SignTx()
    m.transaction = NEM2TransactionCommon()
    m.transaction.network_type = network_type
    m.transaction.type = tx_type
    m.transaction.version = version
    m.transaction.max_fee = max_fee
    m.transaction.deadline = deadline
    m.transfer = NEM2TransferTransaction()
    m.transfer.recipient_address = NEM2RecipientAddress(
        address=recipient_address["address"],
        network_type=recipient_address["network_type"]
    )
    m.transfer.message = NEM2TransferMessage(payload=message["payload"], type=message["type"])
    m.transfer.mosaics = list()
    for i in mosaics:
        m.transfer.mosaics.append(NEM2Mosaic(id=i["id"], amount=i["amount"]))
    return m


if __name__ == '__main__':
    unittest.main()