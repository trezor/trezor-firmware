from common import *

from trezor.crypto import hashlib

if not utils.BITCOIN_ONLY:
    from apps.nem2.helpers import *
    from apps.nem2.mosaic import *
    from apps.nem2.namespace import *
    from apps.nem2.namespace.serialize import *
    from trezor.messages.NEM2MosaicAliasTransaction import NEM2MosaicAliasTransaction


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestNem2Namespace(unittest.TestCase):

    def test_create_mosaic_alias(self):

        transaction=NEM2TransactionCommon(
            network_type=NEM2_NETWORK_TEST_NET,
            type=NEM2_TRANSACTION_TYPE_MOSAIC_ALIAS,
            version=38913,
            max_fee="20000",
            deadline="113248176649"
        )

        mosaic_alias=NEM2MosaicAliasTransaction(
            alias_action=NEM2_ALIAS_ACTION_TYPE_LINK,
            namespace_id="EAA4CB0862DBCB67",
            mosaic_id="32503CBAF145209D",
        )

        t = serialize_mosaic_alias(transaction, mosaic_alias)
        self.assertEqual(t, unhexlify('91000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001984E43204E000000000000090A1E5E1A00000067CBDB6208CBA4EA9D2045F1BA3C503201'))

if __name__ == '__main__':
    unittest.main()