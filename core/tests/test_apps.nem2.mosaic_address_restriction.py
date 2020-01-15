from common import *

from ubinascii import unhexlify, hexlify

if not utils.BITCOIN_ONLY:
    from apps.nem2.helpers import *
    from apps.nem2.mosaic_restriction.serialize import serialize_address_restriction
    from trezor.messages.NEM2TransactionCommon import NEM2TransactionCommon
    from trezor.messages.NEM2MosaicAddressRestrictionTransaction import NEM2MosaicAddressRestrictionTransaction
    from trezor.messages.NEM2Address import NEM2Address

@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestNem2MosaicAddressRestriction(unittest.TestCase):

    def test_serialize_mosaic_address_restriction(self):
        common = NEM2TransactionCommon(
            network_type=NEM2_NETWORK_TEST_NET,
            type=NEM2_TRANSACTION_TYPE_MOSAIC_ADDRESS_RESTRICTION,
            version=38913,
            max_fee=0,
            deadline=113248176649
        )

        address_restriction_transaction = NEM2MosaicAddressRestrictionTransaction(
            mosaic_id="0DC67FBE1CAD29E3",
            restriction_key="0000000000000457",
            previous_restriction_value="1",
            new_restriction_value="2",
            target_address = NEM2Address(
                address = "TCOYOMZ3LEF6ZCHCNKEWLVTYCLSPUBSBTTAM6F2D",
                network_type = NEM2_NETWORK_TEST_NET
            ),
        )

        tx = serialize_address_restriction(common, address_restriction_transaction)
        self.assertEqual(tx, unhexlify('B90000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000019851420000000000000000090A1E5E1A000000E329AD1CBE7FC60D570400000000000001000000000000000200000000000000989D87333B590BEC88E26A8965D67812E4FA06419CC0CF1743'))

if __name__ == '__main__':
    unittest.main()
