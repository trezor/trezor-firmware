from common import *

from trezor.crypto import hashlib

if not utils.BITCOIN_ONLY:
    from apps.nem2.helpers import (
        NEM2_NETWORK_TEST_NET,
        NEM2_TRANSACTION_TYPE_NAMESPACE_METADATA,
    )
    from apps.nem2.metadata.serialize import (
        serialize_namespace_metadata
    )
    from trezor.messages.NEM2TransactionCommon import NEM2TransactionCommon
    from trezor.messages.NEM2Address import NEM2Address
    from trezor.messages.NEM2NamespaceMetadataTransaction import NEM2NamespaceMetadataTransaction


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestNEM2NamespaceMetadata(unittest.TestCase):

    def test_create_namespace_metadata(self):

        transaction=NEM2TransactionCommon(
            network_type=NEM2_NETWORK_TEST_NET,
            type=NEM2_TRANSACTION_TYPE_NAMESPACE_METADATA,
            version=38913,
            max_fee="20000",
            deadline="113248176649"
        )

        namespace_registration=NEM2NamespaceMetadataTransaction(
            target_public_key="252D2E9F95C4671EEB0C67C6666890567E35976B32666263CD390FC188CCF317",
            scoped_metadata_key="0000000000000001",
            value_size_delta=9,
            target_namespace_id="EAA4CB0862DBCB67",
            value_size=9,
            value="4E65772056616C7565"
        )

        t = serialize_namespace_metadata(transaction, namespace_registration)

        self.assertEqual(t, unhexlify('BD000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001984443204E000000000000090A1E5E1A000000252D2E9F95C4671EEB0C67C6666890567E35976B32666263CD390FC188CCF317010000000000000067CBDB6208CBA4EA090009004E65772056616C7565'))

if __name__ == '__main__':
    unittest.main()