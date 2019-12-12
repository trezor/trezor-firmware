from common import *

if not utils.BITCOIN_ONLY:
    from apps.nem2.helpers import *
    from apps.nem2.transfer.serialize import serialize_transfer_body, serialize_transfer
    from apps.nem2.aggregate.serialize import (
        compute_inner_transaction_hash,
        serialize_inner_transactions,
        serialize_aggregate_transaction_body,
        serialize_aggregate_transaction
    )
    from apps.nem2.writers import serialize_embedded_tx_common
    from trezor.messages.NEM2TransferTransaction import NEM2TransferTransaction
    from trezor.messages.NEM2MosaicDefinitionTransaction import NEM2MosaicDefinitionTransaction
    from trezor.messages.NEM2Mosaic import NEM2Mosaic
    from trezor.messages.NEM2TransferMessage import NEM2TransferMessage
    from trezor.messages.NEM2Address import NEM2Address
    from trezor.messages.NEM2EmbeddedTransactionCommon import NEM2EmbeddedTransactionCommon
    from trezor.messages.NEM2TransactionCommon import NEM2TransactionCommon
    from trezor.messages.NEM2AggregateTransaction import NEM2AggregateTransaction
    from trezor.messages.NEM2InnerTransaction import NEM2InnerTransaction

@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestNem2Aggregate(unittest.TestCase):

    # Create mock data to use throughout most of the aggregate transaction tests
    def setUp(self):

        self.transfer_transactions = [
            {
                "common":  NEM2EmbeddedTransactionCommon(
                    network_type = NEM2_NETWORK_MIJIN_TEST,
                    type = NEM2_TRANSACTION_TYPE_TRANSFER,
                    version = 36865,
                    public_key = "BBCE621C6DAB03ECB620356EC029BF74B417E734A699970ADFE504C0CE9EE8AD"
                ),
                "body": NEM2TransferTransaction(
                    recipient_address = NEM2Address(
                        address = "SAAXKRVD6HLAN6IHYM7YWTS3W2BGYXCRBNSA4Q6Y",
                        network_type = NEM2_NETWORK_MIJIN_TEST
                    ),
                    message = NEM2TransferMessage(
                        payload = "send 100 cat.currency to distributor",
                        type = 0
                    ),
                    mosaics = [
                        NEM2Mosaic(
                            id = "9adf3b117a3c10ca",
                            amount = 100
                        )
                    ]
                )
            },
            {
                "common": NEM2EmbeddedTransactionCommon(
                    network_type = NEM2_NETWORK_MIJIN_TEST,
                    type = NEM2_TRANSACTION_TYPE_TRANSFER,
                    version = 36865,
                    public_key = "596FEAB15D98BFD75F1743E9DC8A36474A3D0C06AE78ED134C231336C38A6297"
                ),
                "body": NEM2TransferTransaction(
                    recipient_address = NEM2Address(
                        address = "SDR6OBOYSGCWVQDYJ4ISLXFDZXFZ3FCY3ZLJKI57",
                        network_type = NEM2_NETWORK_MIJIN_TEST
                    ),
                    message = NEM2TransferMessage(
                        payload = "send 1 museum ticket to alice",
                        type = 0
                    ),
                    mosaics = [
                        NEM2Mosaic(
                            id = "7cdf3b117a3c40cc",
                            amount = 1
                        )
                    ]
                )
            },
        ]
        self.mosaic_definition_transactions = [
            {
                "common": NEM2EmbeddedTransactionCommon(
                    network_type = NEM2_NETWORK_MIJIN_TEST,
                    type = NEM2_TRANSACTION_TYPE_MOSAIC_DEFINITION,
                    version = 36865,
                    public_key = "596FEAB15D98BFD75F1743E9DC8A36474A3D0C06AE78ED134C231336C38A6297"
                ),
                "body": NEM2MosaicDefinitionTransaction(
                    mosaic_id = "3F127E74B309F220",
                    duration = 123,
                    nonce = 3095715558,
                    flags = 7,
                    divisibility = 100
                )
            },
        ]

    def test_compute_inner_transaction_hash(self):

        inner_transactions = [
            NEM2InnerTransaction(
                common = self.transfer_transactions[0]["common"],
                transfer = self.transfer_transactions[0]["body"]
            ),
            NEM2InnerTransaction(
                common = self.transfer_transactions[1]["common"],
                transfer = self.transfer_transactions[1]["body"]
            )
            ]
        root_hash = compute_inner_transaction_hash(inner_transactions)
        self.assertEqual(root_hash, unhexlify('6e297f89ec32ef9cab99eb34f58ef2b9436cb46a6f2f28a047b4e0b2ea69553a'))

    def test_serialize_inner_transactions(self):

        inner_transactions = [
            NEM2InnerTransaction(
                common = self.transfer_transactions[0]["common"],
                transfer = self.transfer_transactions[0]["body"]
            ),
            NEM2InnerTransaction(
                common = self.transfer_transactions[1]["common"],
                transfer = self.transfer_transactions[1]["body"]
            )
        ]
        txs = serialize_inner_transactions(inner_transactions)
        self.assertEqual(txs, unhexlify('8500000000000000bbce621c6dab03ecb620356ec029bf74b417e734a699970adfe504c0ce9ee8ad000000000190544190017546a3f1d606f907c33f8b4e5bb6826c5c510b640e43d801250000000000ca103c7a113bdf9a64000000000000000073656e6420313030206361742e63757272656e637920746f206469737472696275746f720000007e00000000000000596feab15d98bfd75f1743e9dc8a36474a3d0c06ae78ed134c231336c38a6297000000000190544190e3e705d891856ac0784f1125dca3cdcb9d9458de569523bf011e0000000000cc403c7a113bdf7c01000000000000000073656e642031206d757365756d207469636b657420746f20616c6963650000'))


    def test_serialize_aggregate_transaction_body_only(self):

        inner_transactions_hash = unhexlify("3b3c45233b537967ed4f6cef0f854983722a09745173ee4df82e15b05582e9f2")
        inner_transactions_serialized = unhexlify("8500000000000000bbce621c6dab03ecb620356ec029bf74b417e734a699970adfe504c0ce9ee8ad000000000190544190017546a3f1d606f907c33f8b4e5bb6826c5c510b640e43d801250000000000ca103c7a113bdf9a64000000000000000073656e6420313030206361742e63757272656e637920746f206469737472696275746f720000007e00000000000000596feab15d98bfd75f1743e9dc8a36474a3d0c06ae78ed134c231336c38a6297000000000190544190e3e705d891856ac0784f1125dca3cdcb9d9458de569523bf011e0000000000cc403c7a113bdf7c01000000000000000073656e642031206d757365756d207469636b657420746f20616c6963650000")

        tx_body = serialize_aggregate_transaction_body(inner_transactions_hash, inner_transactions_serialized)
        self.assertEqual(tx_body, unhexlify('3b3c45233b537967ed4f6cef0f854983722a09745173ee4df82e15b05582e9f208010000000000008500000000000000bbce621c6dab03ecb620356ec029bf74b417e734a699970adfe504c0ce9ee8ad000000000190544190017546a3f1d606f907c33f8b4e5bb6826c5c510b640e43d801250000000000ca103c7a113bdf9a64000000000000000073656e6420313030206361742e63757272656e637920746f206469737472696275746f720000007e00000000000000596feab15d98bfd75f1743e9dc8a36474a3d0c06ae78ed134c231336c38a6297000000000190544190e3e705d891856ac0784f1125dca3cdcb9d9458de569523bf011e0000000000cc403c7a113bdf7c01000000000000000073656e642031206d757365756d207469636b657420746f20616c6963650000'))

    # AggregateBonded
    # This test uses two TransferTransactions as part of the AggregateTransaction
    def test_serialize_aggregate_bonded_transfer_transaction(self):

        inner_transactions = [
            NEM2InnerTransaction(
                common = self.transfer_transactions[0]["common"],
                transfer = self.transfer_transactions[0]["body"]
            ),
            NEM2InnerTransaction(
                common = self.transfer_transactions[1]["common"],
                transfer = self.transfer_transactions[1]["body"]
            )
        ]

        aggregate_transaction = NEM2AggregateTransaction(
            inner_transactions = inner_transactions
        )

        common = NEM2TransactionCommon(
            network_type = NEM2_NETWORK_MIJIN_TEST,
            type = NEM2_TRANSACTION_TYPE_AGGREGATE_BONDED,
            version = 36865,
            max_fee = 100,
            deadline = "113248176649"
        )

        tx = serialize_aggregate_transaction(common, aggregate_transaction)
        self.assertEqual(tx, unhexlify('b00100000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000019041426400000000000000090a1e5e1a0000006e297f89ec32ef9cab99eb34f58ef2b9436cb46a6f2f28a047b4e0b2ea69553a08010000000000008500000000000000bbce621c6dab03ecb620356ec029bf74b417e734a699970adfe504c0ce9ee8ad000000000190544190017546a3f1d606f907c33f8b4e5bb6826c5c510b640e43d801250000000000ca103c7a113bdf9a64000000000000000073656e6420313030206361742e63757272656e637920746f206469737472696275746f720000007e00000000000000596feab15d98bfd75f1743e9dc8a36474a3d0c06ae78ed134c231336c38a6297000000000190544190e3e705d891856ac0784f1125dca3cdcb9d9458de569523bf011e0000000000cc403c7a113bdf7c01000000000000000073656e642031206d757365756d207469636b657420746f20616c6963650000'))

    # AggregateBonded
    # This test uses a TransferTransaction and a MosaicDefinition transaction as part of the AggregateTransaction
    def test_serialize_aggregate_bonded_transfer_and_mosaic_transaction(self):

        inner_transactions = [
            NEM2InnerTransaction(
                common = self.transfer_transactions[0]["common"],
                transfer = self.transfer_transactions[0]["body"]
            ),
            NEM2InnerTransaction(
                common = self.mosaic_definition_transactions[0]["common"],
                mosaic_definition = self.mosaic_definition_transactions[0]["body"]
            )
        ]

        aggregate_transaction = NEM2AggregateTransaction(
            inner_transactions = inner_transactions
        )

        common = NEM2TransactionCommon(
            network_type = NEM2_NETWORK_MIJIN_TEST,
            type = NEM2_TRANSACTION_TYPE_AGGREGATE_BONDED,
            version = 36865,
            max_fee = 100,
            deadline = 113728610090
        )

        tx = serialize_aggregate_transaction(common, aggregate_transaction)
        self.assertEqual(tx, unhexlify('7801000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000190414264000000000000002ADFC07A1A000000E114E6428F83FE97E532F4698A4181B2BE859850CA43E63D7BBB0E73AA6850BBD0000000000000008500000000000000BBCE621C6DAB03ECB620356EC029BF74B417E734A699970ADFE504C0CE9EE8AD000000000190544190017546A3F1D606F907C33F8B4E5BB6826C5C510B640E43D801250000000000CA103C7A113BDF9A64000000000000000073656E6420313030206361742E63757272656E637920746F206469737472696275746F720000004600000000000000596FEAB15D98BFD75F1743E9DC8A36474A3D0C06AE78ED134C231336C38A62970000000001904D4120F209B3747E123F7B00000000000000E6DE84B807640000'))

    # AggregateComplete
    # This test uses a TransferTransaction and a MosaicDefinition transaction as part of the AggregateTransaction
    def test_serialize_aggregate_complete_transfer_and_mosaic_transaction(self):

        inner_transactions = [
            NEM2InnerTransaction(
                common = self.transfer_transactions[0]["common"],
                transfer = self.transfer_transactions[0]["body"]
            ),
            NEM2InnerTransaction(
                common = self.mosaic_definition_transactions[0]["common"],
                mosaic_definition = self.mosaic_definition_transactions[0]["body"]
            )
        ]

        aggregate_transaction = NEM2AggregateTransaction(
            inner_transactions = inner_transactions
        )

        common = NEM2TransactionCommon(
            network_type = NEM2_NETWORK_MIJIN_TEST,
            type = NEM2_TRANSACTION_TYPE_AGGREGATE_COMPLETE,
            version = 36865,
            max_fee = 100,
            deadline = 113728610090
        )

        tx = serialize_aggregate_transaction(common, aggregate_transaction)
        self.assertEqual(tx, unhexlify('7801000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000190414164000000000000002ADFC07A1A000000E114E6428F83FE97E532F4698A4181B2BE859850CA43E63D7BBB0E73AA6850BBD0000000000000008500000000000000BBCE621C6DAB03ECB620356EC029BF74B417E734A699970ADFE504C0CE9EE8AD000000000190544190017546A3F1D606F907C33F8B4E5BB6826C5C510B640E43D801250000000000CA103C7A113BDF9A64000000000000000073656E6420313030206361742E63757272656E637920746F206469737472696275746F720000004600000000000000596FEAB15D98BFD75F1743E9DC8A36474A3D0C06AE78ED134C231336C38A62970000000001904D4120F209B3747E123F7B00000000000000E6DE84B807640000'))

if __name__ == '__main__':
    unittest.main()
