from common import *

from ubinascii import unhexlify, hexlify

if not utils.BITCOIN_ONLY:
    from apps.nem2.helpers import *
    from apps.nem2.account_link.serialize import serialize_account_link
    from trezor.messages.NEM2TransactionCommon import NEM2TransactionCommon
    from trezor.messages.NEM2AccountLinkTransaction import NEM2AccountLinkTransaction

@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestNem2AccountLink(unittest.TestCase):

    def test_serialize_account_link(self):
        common = NEM2TransactionCommon(
            network_type=NEM2_NETWORK_TEST_NET,
            type=NEM2_TRANSACTION_TYPE_ACCOUNT_LINK,
            version=38913,
            max_fee=0,
            deadline=113248176649
        )

        account_link_transaction = NEM2AccountLinkTransaction(
            remote_public_key="51585DA12749432888AC492B4D3AB7E5AAC0108773ED12A01EC8EB8EECA1D820",
            link_action=1
        )

        tx = serialize_account_link(common, account_link_transaction)
        self.assertEqual(tx, unhexlify('A1000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001984C410000000000000000090A1E5E1A00000051585DA12749432888AC492B4D3AB7E5AAC0108773ED12A01EC8EB8EECA1D82001'))

if __name__ == '__main__':
    unittest.main()
