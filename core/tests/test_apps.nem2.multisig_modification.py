from common import *

from trezor.crypto import hashlib

if not utils.BITCOIN_ONLY:
    from apps.nem2.helpers import (
        NEM2_NETWORK_TEST_NET,
        NEM2_TRANSACTION_TYPE_MULTISIG_MODIFICATION,
    )
    from apps.nem2.multisig.serialize import (
        serialize_multisig_modification
    )
    from trezor.messages.NEM2TransactionCommon import NEM2TransactionCommon
    from trezor.messages.NEM2Address import NEM2Address
    from trezor.messages.NEM2MultisigModificationTransaction import NEM2MultisigModificationTransaction


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestNEM2NamespaceMetadata(unittest.TestCase):

    def test_create_serialize_multisig_modification_add_public_key(self):

        transaction=NEM2TransactionCommon(
            network_type=NEM2_NETWORK_TEST_NET,
            type=NEM2_TRANSACTION_TYPE_MULTISIG_MODIFICATION,
            version=38913,
            max_fee="100",
            deadline="113248176649"
        )

        namespace_registration=NEM2MultisigModificationTransaction(
            min_approval_delta=1,
            min_removal_delta=1,
            public_key_additions=["596FEAB15D98BFD75F1743E9DC8A36474A3D0C06AE78ED134C231336C38A6297"],
            public_key_deletions=[],
        )

        t = serialize_multisig_modification(transaction, namespace_registration)

        self.assertEqual(t, unhexlify('A80000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000019855416400000000000000090A1E5E1A0000000101010000000000596FEAB15D98BFD75F1743E9DC8A36474A3D0C06AE78ED134C231336C38A6297'))

    def test_create_serialize_multisig_modification_remove_public_key(self):

        transaction=NEM2TransactionCommon(
            network_type=NEM2_NETWORK_TEST_NET,
            type=NEM2_TRANSACTION_TYPE_MULTISIG_MODIFICATION,
            version=38913,
            max_fee="100",
            deadline="113248176649"
        )

        namespace_registration=NEM2MultisigModificationTransaction(
            min_approval_delta=-1,
            min_removal_delta=-1,
            public_key_additions=[],
            public_key_deletions=["596FEAB15D98BFD75F1743E9DC8A36474A3D0C06AE78ED134C231336C38A6297"],
        )

        t = serialize_multisig_modification(transaction, namespace_registration)

        self.assertEqual(t, unhexlify('A80000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000019855416400000000000000090A1E5E1A000000FFFF000100000000596FEAB15D98BFD75F1743E9DC8A36474A3D0C06AE78ED134C231336C38A6297'))

    def test_create_serialize_multisig_modification_extreme_deltas(self):

        transaction=NEM2TransactionCommon(
            network_type=NEM2_NETWORK_TEST_NET,
            type=NEM2_TRANSACTION_TYPE_MULTISIG_MODIFICATION,
            version=38913,
            max_fee="100",
            deadline="113248176649"
        )

        namespace_registration=NEM2MultisigModificationTransaction(
            min_approval_delta=-120,
            min_removal_delta=115,
            public_key_additions=[],
            public_key_deletions=["596FEAB15D98BFD75F1743E9DC8A36474A3D0C06AE78ED134C231336C38A6297"],
        )

        t = serialize_multisig_modification(transaction, namespace_registration)

        self.assertEqual(t, unhexlify('A80000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000019855416400000000000000090A1E5E1A0000007388000100000000596FEAB15D98BFD75F1743E9DC8A36474A3D0C06AE78ED134C231336C38A6297'))

if __name__ == '__main__':
    unittest.main()