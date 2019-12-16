from common import *

if not utils.BITCOIN_ONLY:
    from apps.nem2.helpers import *
    from apps.nem2.account_restriction.serialize import serialize_account_restriction
    from apps.nem2.writers import serialize_embedded_tx_common
    from trezor.messages.NEM2TransactionCommon import NEM2TransactionCommon
    from trezor.messages.NEM2AccountAddressRestrictionTransaction import NEM2AccountAddressRestrictionTransaction
    from trezor.messages.NEM2AccountMosaicRestrictionTransaction import NEM2AccountMosaicRestrictionTransaction
    from trezor.messages.NEM2AccountOperationRestrictionTransaction import NEM2AccountOperationRestrictionTransaction
    from trezor.messages.NEM2Address import NEM2Address

@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestNem2AccountAddressRestriction(unittest.TestCase):

    def test_account_address_restriction(self):
        common = NEM2TransactionCommon(
            network_type=NEM2_NETWORK_TEST_NET,
            type=NEM2_TRANSACTION_TYPE_ACCOUNT_ADDRESS_RESTRICTION,
            version=38913,
            max_fee=0,
            deadline=113248176649
        )

        account_address_restriction_transaction = NEM2AccountAddressRestrictionTransaction(
            restriction_type=NEM2_ACCOUNT_RESTRICTION_ALLOW_INCOMING_ADDRESS,
            restriction_additions=[
                NEM2Address(
                    address="TBXH7SBBRXI4BECXRXR54VIRZR34YN75LZ3ZRRC3",
                    network_type=NEM2_NETWORK_TEST_NET
                )
            ],
            restriction_deletions=[
                NEM2Address(
                    address="TBRL2IM33LWRHIDNVMO6M6LPBQ2CUS67KI7XJDCZ",
                    network_type=NEM2_NETWORK_TEST_NET
                ),
                NEM2Address(
                    address="TAWIV4Y5YACUYEP3BPCGS27ERBPOF34CVZXYYZN7",
                    network_type=NEM2_NETWORK_TEST_NET
                )
            ]
        )

        tx = serialize_account_restriction(common, account_address_restriction_transaction)
        self.assertEqual(tx, unhexlify('D30000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000019850410000000000000000090A1E5E1A0000000100010200000000986E7FC8218DD1C090578DE3DE5511CC77CC37FD5E7798C45B9862BD219BDAED13A06DAB1DE6796F0C342A4BDF523F748C59982C8AF31DC0054C11FB0BC4696BE4885EE2EF82AE6F8C65BF'))

    def test_account_mosaic_restriction(self):
        common = NEM2TransactionCommon(
            network_type=NEM2_NETWORK_TEST_NET,
            type=NEM2_TRANSACTION_TYPE_ACCOUNT_MOSAIC_RESTRICTION,
            version=38913,
            max_fee=0,
            deadline=113248176649
        )

        account_mosaic_restriction_transaction = NEM2AccountMosaicRestrictionTransaction(
            restriction_type=NEM2_ACCOUNT_RESTRICTION_BLOCK_MOSAIC,
            restriction_additions=["9ADF3B117A3C10CA"],
            restriction_deletions=[]
        )

        tx = serialize_account_restriction(common, account_mosaic_restriction_transaction)
        self.assertEqual(tx, unhexlify('900000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000019850420000000000000000090A1E5E1A0000000280010000000000CA103C7A113BDF9A'))
    
    def test_account_operation_restriction(self):
        common = NEM2TransactionCommon(
            network_type=NEM2_NETWORK_TEST_NET,
            type=NEM2_TRANSACTION_TYPE_ACCOUNT_OPERATION_RESTRICTION,
            version=38913,
            max_fee=0,
            deadline=113248176649
        )

        account_operation_restriction_transaction = NEM2AccountOperationRestrictionTransaction(
            restriction_type=NEM2_ACCOUNT_RESTRICTION_ALLOW_INCOMING_TRANSACTION_TYPE,
            restriction_additions=[NEM2_TRANSACTION_TYPE_ACCOUNT_METADATA, NEM2_TRANSACTION_TYPE_MOSAIC_ALIAS],
            restriction_deletions=[NEM2_TRANSACTION_TYPE_HASH_LOCK]
        )

        tx = serialize_account_restriction(common, account_operation_restriction_transaction)
        self.assertEqual(tx, unhexlify('8E0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000019850430000000000000000090A1E5E1A000000040002010000000044414E434841'))

if __name__ == '__main__':
    unittest.main()
