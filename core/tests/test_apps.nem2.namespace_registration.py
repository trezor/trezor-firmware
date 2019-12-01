from common import *

from trezor.crypto import hashlib

if not utils.BITCOIN_ONLY:
    from apps.nem2.helpers import *
    from apps.nem2.mosaic import *
    from apps.nem2.namespace import *
    from apps.nem2.namespace.serialize import *
    from trezor.messages.NEM2TransferTransaction import NEM2TransferTransaction
    from trezor.messages.NEM2SignTx import NEM2SignTx
    from trezor.messages.NEM2Mosaic import NEM2Mosaic
    from trezor.messages.NEM2TransferMessage import NEM2TransferMessage
    from trezor.messages.NEM2RecipientAddress import NEM2RecipientAddress


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestNem2NamespaceRegistration(unittest.TestCase):

    def test_create_root_namespace_registration(self):

        transaction=NEM2TransactionCommon(
            network_type=NEM2_NETWORK_TEST_NET,
            type=NEM2_TRANSACTION_TYPE_NAMESPACE_REGISTRATION,
            version=38913,
            max_fee="20000",
            deadline="113248176649"
        )

        namespace_registration=NEM2NamespaceRegistrationTransaction(
            registration_type=NEM2_NAMESPACE_REGISTRATION_TYPE_ROOT,
            namespace_name="testnamespace".encode(),
            id=int("EAA4CB0862DBCB67", 16),
            duration=int("1000000")
        )

        t = serialize_namespace_registration(transaction, namespace_registration)

        self.assertEqual(t, unhexlify('9F000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001984E41204E000000000000090A1E5E1A00000040420F000000000067CBDB6208CBA4EA000D746573746E616D657370616365'))
        # self.assertEqual(hashlib.sha3_256(t, keccak=True).digest(), unhexlify('0acbf8df91e6a65dc56c56c43d65f31ff2a6a48d06fc66e78c7f3436faf3e74f'))

if __name__ == '__main__':
    unittest.main()