from common import *

if not utils.BITCOIN_ONLY:
    from apps.nem2.helpers import *
    from apps.nem2.secret_lock.serialize import serialize_secret_lock
    from apps.nem2.writers import serialize_embedded_tx_common
    from trezor.messages.NEM2TransactionCommon import NEM2TransactionCommon
    from trezor.messages.NEM2SecretLockTransaction import NEM2SecretLockTransaction
    from trezor.messages.NEM2Mosaic import NEM2Mosaic
    from trezor.messages.NEM2Address import NEM2Address

@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestNem2SecretLock(unittest.TestCase):
    def test_serialize_secret_lock(self):
        common = NEM2TransactionCommon(
            network_type=NEM2_NETWORK_MIJIN,
            type=NEM2_TRANSACTION_TYPE_SECRET_LOCK,
            version=24577,
            max_fee=0,
            deadline=113728610090
        )

        secret_lock_transaction = NEM2SecretLockTransaction(
            secret="D77E46ED5EC0EA4BD08AA77EEA9F17076F40BC2C2843B1BBB46DAA1D98DBF1B7",
            mosaic=NEM2Mosaic(
                id="9adf3b117a3c10ca",
                amount=10
            ),
            duration=23040,
            hash_algorithm=NEM2_SECRET_LOCK_SHA3_256,
            recipient_address=NEM2Address(
                address="MAJNLQOD7TBPI4EAUHZNTXLSEA4IHVQTH54XTOUV",
                network_type=NEM2_NETWORK_MIJIN
            ),
        )

        tx = serialize_secret_lock(common, secret_lock_transaction)
        self.assertEqual(tx, unhexlify('D200000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000160524100000000000000002ADFC07A1A000000D77E46ED5EC0EA4BD08AA77EEA9F17076F40BC2C2843B1BBB46DAA1D98DBF1B7CA103C7A113BDF9A0A00000000000000005A000000000000006012D5C1C3FCC2F47080A1F2D9DD72203883D6133F7979BA95'))

if __name__ == '__main__':
    unittest.main()
