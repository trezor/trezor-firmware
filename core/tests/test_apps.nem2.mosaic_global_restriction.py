from common import *

from ubinascii import unhexlify, hexlify

if not utils.BITCOIN_ONLY:
    from apps.nem2.helpers import *
    from apps.nem2.mosaic_restriction.serialize import serialize_global_restriction
    from trezor.messages.NEM2TransactionCommon import NEM2TransactionCommon
    from trezor.messages.NEM2MosaicGlobalRestrictionTransaction import NEM2MosaicGlobalRestrictionTransaction

@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestNem2MosaicGlobalRestriction(unittest.TestCase):

    def test_serialize_mosaic_global_restriction(self):
        common = NEM2TransactionCommon(
            network_type=NEM2_NETWORK_TEST_NET,
            type=NEM2_TRANSACTION_TYPE_MOSAIC_GLOBAL_TRANSACTION,
            version=38913,
            max_fee=0,
            deadline=113248176649
        )

        global_restriction_transaction = NEM2MosaicGlobalRestrictionTransaction(
            mosaic_id="0DC67FBE1CAD29E3",
            reference_mosaic_id="0B65C4B29A80C619",
            restriction_key="0000000000000457",
            previous_restriction_value="1",
            previous_restriction_type=1,
            new_restriction_value="2",
            new_restriction_type=1
        )

        tx = serialize_global_restriction(common, global_restriction_transaction)
        self.assertEqual(tx, unhexlify('AA0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000019851410000000000000000090A1E5E1A000000E329AD1CBE7FC60D19C6809AB2C4650B5704000000000000010000000000000002000000000000000101'))

if __name__ == '__main__':
    unittest.main()
