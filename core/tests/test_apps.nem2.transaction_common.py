from common import *

from trezor.crypto import hashlib

if not utils.BITCOIN_ONLY:
    from apps.nem2.helpers import *
    from apps.nem2.transfer.serialize import *
    from apps.nem2.writers import serialize_embedded_tx_common
    from trezor.messages.NEM2EmbeddedTransactionCommon import NEM2EmbeddedTransactionCommon


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestNem2TransactionCommon(unittest.TestCase):

    def test_create_embedded_transaction_common(self):

        embedded_transaction = NEM2EmbeddedTransactionCommon(
            network_type = NEM2_NETWORK_MIJIN_TEST,
            type = NEM2_TRANSACTION_TYPE_TRANSFER,
            version = 36865,
            public_key = "596FEAB15D98BFD75F1743E9DC8A36474A3D0C06AE78ED134C231336C38A6297"
        )

        tx = bytearray()
        t = serialize_embedded_tx_common(tx, embedded_transaction)

        self.assertEqual(t, unhexlify('00000000596feab15d98bfd75f1743e9dc8a36474a3d0c06ae78ed134c231336c38a62970000000001905441'))

if __name__ == '__main__':
    unittest.main()