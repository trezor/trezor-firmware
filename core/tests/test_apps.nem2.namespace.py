from common import *

from trezor.crypto import hashlib

if not utils.BITCOIN_ONLY:
    from apps.nem2.helpers import (
        NEM2_NETWORK_TEST_NET,
        NEM2_TRANSACTION_TYPE_NAMESPACE_REGISTRATION,
        NEM2_TRANSACTION_TYPE_ADDRESS_ALIAS,
        NEM2_NAMESPACE_REGISTRATION_TYPE_ROOT,
        NEM2_NAMESPACE_REGISTRATION_TYPE_SUB,
        NEM2_ALIAS_ACTION_LINK,
        NEM2_ALIAS_ACTION_UNLINK
    )
    from apps.nem2.namespace.serialize import (
        serialize_namespace_registration,
        serialize_address_alias
    )
    from trezor.messages.NEM2TransactionCommon import NEM2TransactionCommon
    from trezor.messages.NEM2Address import NEM2Address
    from trezor.messages.NEM2NamespaceRegistrationTransaction import NEM2NamespaceRegistrationTransaction
    from trezor.messages.NEM2AddressAliasTransaction import NEM2AddressAliasTransaction


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
            namespace_name="testnamespace",
            id="EAA4CB0862DBCB67",
            duration="1000000"
        )

        t = serialize_namespace_registration(transaction, namespace_registration)

        self.assertEqual(t, unhexlify('9F000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001984E41204E000000000000090A1E5E1A00000040420F000000000067CBDB6208CBA4EA000D746573746E616D657370616365'))

    def test_create_child_namespace_registration(self):

        transaction=NEM2TransactionCommon(
            network_type=NEM2_NETWORK_TEST_NET,
            type=NEM2_TRANSACTION_TYPE_NAMESPACE_REGISTRATION,
            version=38913,
            max_fee="20000",
            deadline="113248176649"
        )

        namespace_registration=NEM2NamespaceRegistrationTransaction(
            registration_type=NEM2_NAMESPACE_REGISTRATION_TYPE_SUB,
            namespace_name="sub",
            parent_id="EAA4CB0862DBCB67",
            id="B1B6FADB51C1368C"
        )

        t = serialize_namespace_registration(transaction, namespace_registration)

        self.assertEqual(t, unhexlify('95000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001984E41204E000000000000090A1E5E1A00000067CBDB6208CBA4EA8C36C151DBFAB6B10103737562'))

    def test_create_link_address_alias(self):

        transaction=NEM2TransactionCommon(
            network_type=NEM2_NETWORK_TEST_NET,
            type=NEM2_TRANSACTION_TYPE_ADDRESS_ALIAS,
            version=38913,
            max_fee="20000",
            deadline="113248176649"
        )

        address_alias=NEM2AddressAliasTransaction(
            namespace_id="EAA4CB0862DBCB67",
            address=NEM2Address(
                address="TD7FI2VK7ZRCPDRUII62XL567V72IPO5CBXPM2C3",
                network_type=NEM2_NETWORK_TEST_NET
            ),
            alias_action=NEM2_ALIAS_ACTION_LINK
        )

        t = serialize_address_alias(transaction, address_alias)

        self.assertEqual(t, unhexlify('A2000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001984E42204E000000000000090A1E5E1A00000067CBDB6208CBA4EA98FE546AAAFE62278E34423DABAFBEFD7FA43DDD106EF6685B01'))

if __name__ == '__main__':
    unittest.main()