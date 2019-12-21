from common import *

if not utils.BITCOIN_ONLY:
    from apps.nem2.helpers import *
    from apps.nem2.mosaic import *
    from apps.nem2.transfer import *
    from apps.nem2.transfer.serialize import *
    from trezor.messages.NEM2TransferTransaction import NEM2TransferTransaction
    from trezor.messages.NEM2TransactionCommon import NEM2TransactionCommon
    from trezor.messages.NEM2EmbeddedTransactionCommon import NEM2EmbeddedTransactionCommon
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

    def test_create_transfer_plain_message_payload(self):

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
            mosaics=[NEM2Mosaic(id="85BBEA6CC462B244", amount=1000000000)]
        )

        t = serialize_transfer(transaction, transfer)

        self.assertEqual(t, unhexlify('BE000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001985441204E000000000000090A1E5E1A000000981DE81282D81E19B06024D86F232947F0EBD8EB30BB3E1C1C010E000000000044B262C46CEABB8500CA9A3B000000000054657374205472616E73666572'))

    def test_create_transfer_encrypted_message_payload(self):

        transaction = NEM2TransactionCommon(
            network_type=NEM2_NETWORK_TEST_NET,
            type=NEM2_TRANSACTION_TYPE_TRANSFER,
            version=38913,
            max_fee="20000",
            deadline="113248176649"
        )

        transfer = NEM2TransferTransaction(
            recipient_address=NEM2Address(
                address="TB6YHDGPYV3TGEFE7Z3BH2EXJZNVJJTH3EWL76PD",
                network_type=NEM2_NETWORK_TEST_NET
            ),
            message=NEM2TransferMessage(
                payload="2F63A2105E85E13BCA7BB16137447B321E60ED03B2FB6DC2470C6262428D3C8B699FA2FC16E10D1557D67A1C36FB90AA56166AB022C0305C9903570EE2C7E3C4",
                type=1
            ),
            mosaics=[NEM2Mosaic(id="85BBEA6CC462B244", amount=1000000000)]
        )

        t = serialize_transfer(transaction, transfer)

        self.assertEqual(t, unhexlify('31010000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001985441204E000000000000090A1E5E1A000000987D838CCFC5773310A4FE7613E8974E5B54A667D92CBFF9E30181000000000044B262C46CEABB8500CA9A3B00000000013246363341323130354538354531334243413742423136313337343437423332314536304544303342324642364443323437304336323632343238443343384236393946413246433136453130443135353744363741314333364642393041413536313636414230323243303330354339393033353730454532433745334334'))

    def test_create_transfer_transaction_body_only(self):

        transfer_transaction_body = NEM2TransferTransaction(
            recipient_address = NEM2RecipientAddress(
                address = "SDR6OBOYSGCWVQDYJ4ISLXFDZXFZ3FCY3ZLJKI57",
                network_type = NEM2_NETWORK_MIJIN_TEST
            ),
            message=NEM2TransferMessage(
                payload="send 1 museum ticket to alice",
                type=0
            ),
            mosaics=[
                NEM2Mosaic(
                    id="7cdf3b117a3c40cc",
                    amount=1
                )
            ]
        )

        t = serialize_transfer_body(transfer_transaction_body)
        self.assertEqual(t, unhexlify('90e3e705d891856ac0784f1125dca3cdcb9d9458de569523bf011e0000000000cc403c7a113bdf7c01000000000000000073656e642031206d757365756d207469636b657420746f20616c696365'))

    def test_create_embedded_transfer_transaction_full(self):

        embedded_common=NEM2EmbeddedTransactionCommon(
            network_type=NEM2_NETWORK_MIJIN_TEST,
            type=NEM2_TRANSACTION_TYPE_TRANSFER,
            version=36865,
            public_key="596FEAB15D98BFD75F1743E9DC8A36474A3D0C06AE78ED134C231336C38A6297"
        )

        transfer_transaction_body=NEM2TransferTransaction(
            recipient_address=NEM2RecipientAddress(
                address="SDR6OBOYSGCWVQDYJ4ISLXFDZXFZ3FCY3ZLJKI57",
                network_type=NEM2_NETWORK_MIJIN_TEST
            ),
            message=NEM2TransferMessage(
                payload="send 1 museum ticket to alice",
                type=0
            ),
            mosaics=[
                NEM2Mosaic(
                    id="7cdf3b117a3c40cc",
                    amount=1
                )
            ]
        )

        t = serialize_transfer(embedded_common, transfer_transaction_body, embedded = True)
        self.assertEqual(t, unhexlify('7e00000000000000596feab15d98bfd75f1743e9dc8a36474a3d0c06ae78ed134c231336c38a6297000000000190544190e3e705d891856ac0784f1125dca3cdcb9d9458de569523bf011e0000000000cc403c7a113bdf7c01000000000000000073656e642031206d757365756d207469636b657420746f20616c696365'))


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

        t = serialize_transfer(transaction, transfer)

        self.assertEqual(t, unhexlify('BE000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001985441204E000000000000090A1E5E1A000000981DE81282D81E19B06024D86F232947F0EBD8EB30BB3E1C1C010E0000000000C47BCD9047148F3000CA9A3B000000000054657374205472616E73666572'))
        # self.assertEqual(hashlib.sha3_256(t, keccak=True).digest(), unhexlify('923EB29CF8C75E9BB03DB064C47389FD98B1EC2A62CD7C685FBA7F706B09DF73'))

if __name__ == '__main__':
    unittest.main()
