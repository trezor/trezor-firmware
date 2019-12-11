from common import *

if not utils.BITCOIN_ONLY:
    from apps.nem2.helpers import *
    from apps.nem2.secret_lock.serialize import serialize_secret_lock, serialize_secret_proof
    from apps.nem2.writers import serialize_embedded_tx_common
    from trezor.messages.NEM2TransactionCommon import NEM2TransactionCommon
    from trezor.messages.NEM2SecretLockTransaction import NEM2SecretLockTransaction
    from trezor.messages.NEM2SecretProofTransaction import NEM2SecretProofTransaction
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

    def test_serialize_secret_proof(self):
        common = NEM2TransactionCommon(
            network_type=NEM2_NETWORK_MAIN_NET,
            type=NEM2_TRANSACTION_TYPE_SECRET_PROOF,
            version=26625,
            max_fee=0,
            deadline=113728610090
        )

        secret_proof_transaction = NEM2SecretProofTransaction(
            secret="D77E46ED5EC0EA4BD08AA77EEA9F17076F40BC2C2843B1BBB46DAA1D98DBF1B7",
            hash_algorithm=NEM2_SECRET_LOCK_SHA3_256,
            recipient_address=NEM2Address(
                address="NABLKWFB5SWIEHJBZNOHJC3N65QO2FR2WZSW6DKZ",
                network_type=NEM2_NETWORK_MAIN_NET
            ),
            proof="a25fde258f078ddce870"
        )

        tx = serialize_secret_proof(common, secret_proof_transaction)
        self.assertEqual(tx, unhexlify('C600000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000168524200000000000000002ADFC07A1A000000D77E46ED5EC0EA4BD08AA77EEA9F17076F40BC2C2843B1BBB46DAA1D98DBF1B70A00006802B558A1ECAC821D21CB5C748B6DF760ED163AB6656F0D59A25FDE258F078DDCE870'))

if __name__ == '__main__':
    unittest.main()
