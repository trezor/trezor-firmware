from common import *

if not utils.BITCOIN_ONLY:
    from apps.nem2.helpers import *
    from apps.nem2.mosaic import *
    from apps.nem2.transfer.serialize import serialize_transfer_body, serialize_transfer
    from apps.nem2.mosaic.serialize import serialize_mosaic_definition
    from apps.nem2.aggregate.serialize import compute_inner_transaction_hash, serialize_inner_transactions, serialize_aggregate_transaction_body, serialize_aggregate_transaction
    from apps.nem2.writers import serialize_embedded_tx_common
    from trezor.messages.NEM2TransferTransaction import NEM2TransferTransaction
    from trezor.messages.NEM2SignTx import NEM2SignTx
    from trezor.messages.NEM2Mosaic import NEM2Mosaic
    from trezor.messages.NEM2TransferMessage import NEM2TransferMessage
    from trezor.messages.NEM2Address import NEM2Address
    from trezor.messages.NEM2EmbeddedTransactionCommon import NEM2EmbeddedTransactionCommon
    from trezor.messages.NEM2InnerTransaction import NEM2InnerTransaction
    from trezor.messages.NEM2MosaicDefinitionTransaction import NEM2MosaicDefinitionTransaction

@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestNem2Mosaic(unittest.TestCase):

    def test_serialize_mosaic_definition(self):

        common = NEM2TransactionCommon(
            network_type = NEM2_NETWORK_TEST_NET,
            type = NEM2_TRANSACTION_TYPE_MOSAIC_DEFINITION,
            version = 38913,
            max_fee = 100,
            deadline = 113728610090
        )

        mosaic_definition = NEM2MosaicDefinitionTransaction(
            mosaic_id = "0B65C4B29A80C619",
            duration = 123,
            nonce = 3095715558,
            flags = 7,
            divisibility = 100
        )

        tx = serialize_mosaic_definition(common, mosaic_definition)
        self.assertEqual(tx, unhexlify('96000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001984D4164000000000000002ADFC07A1A00000019C6809AB2C4650B7B00000000000000E6DE84B80764'))

if __name__ == '__main__':
    unittest.main()
