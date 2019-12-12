from common import *

if not utils.BITCOIN_ONLY:
    from apps.nem2.helpers import *
    from apps.nem2.mosaic import *
    from apps.nem2.mosaic.serialize import serialize_mosaic_definition, serialize_mosaic_supply
    from trezor.messages.NEM2MosaicDefinitionTransaction import NEM2MosaicDefinitionTransaction
    from trezor.messages.NEM2MosaicSupplyChangeTransaction import NEM2MosaicSupplyChangeTransaction

@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestNem2Mosaic(unittest.TestCase):

    def test_serialize_mosaic_definition(self):

        common = NEM2TransactionCommon(
            network_type=NEM2_NETWORK_TEST_NET,
            type=NEM2_TRANSACTION_TYPE_MOSAIC_DEFINITION,
            version=38913,
            max_fee=100,
            deadline=113728610090
        )

        mosaic_definition = NEM2MosaicDefinitionTransaction(
            mosaic_id="0B65C4B29A80C619",
            duration=123,
            nonce=3095715558,
            flags=7,
            divisibility=100
        )

        tx = serialize_mosaic_definition(common, mosaic_definition)
        self.assertEqual(tx, unhexlify('96000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001984D4164000000000000002ADFC07A1A00000019C6809AB2C4650B7B00000000000000E6DE84B80764'))

    def test_serialize_mosaic_supply(self):

        common = NEM2TransactionCommon(
            network_type=NEM2_NETWORK_TEST_NET,
            type=NEM2_TRANSACTION_TYPE_MOSAIC_SUPPLY,
            version=38913,
            max_fee=100,
            deadline=113728610090
        )

        mosaic_supply = NEM2MosaicSupplyChangeTransaction(
            mosaic_id="0B65C4B29A80C619",
            action=NEM2_MOSAIC_SUPPLY_CHANGE_ACTION_INCREASE,
            delta=1000000
        )

        tx = serialize_mosaic_supply(common, mosaic_supply)
        self.assertEqual(tx, unhexlify('91000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001984D4264000000000000002ADFC07A1A00000019C6809AB2C4650B40420F000000000001'))


if __name__ == '__main__':
    unittest.main()
