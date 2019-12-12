from common import *

if not utils.BITCOIN_ONLY:
    from apps.nem2.helpers import *
    from apps.nem2.hash_lock.serialize import serialize_hash_lock
    from trezor.messages.NEM2TransactionCommon import NEM2TransactionCommon
    from trezor.messages.NEM2HashLockTransaction import NEM2HashLockTransaction
    from trezor.messages.NEM2Mosaic import NEM2Mosaic

@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestNem2HashLock(unittest.TestCase):

    def test_serialize_hash_lock(self):
        common = NEM2TransactionCommon(
            network_type=NEM2_NETWORK_MIJIN_TEST,
            type=16712,
            version=36865,
            max_fee=0,
            deadline=113728610090
        )

        hash_lock_transaction = NEM2HashLockTransaction(
            mosaic=NEM2Mosaic(
                id="85BBEA6CC462B244",
                amount=10000000
            ),
            duration=480,
            hash="4FF8C7E00B02D7380900B7795B4CDDC5B9D03536B5BD896BF54F8E5C53F4A32B"
        )

        tx = serialize_hash_lock(common, hash_lock_transaction)
        self.assertEqual(tx, unhexlify('B800000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000190484100000000000000002ADFC07A1A00000044B262C46CEABB858096980000000000E0010000000000004FF8C7E00B02D7380900B7795B4CDDC5B9D03536B5BD896BF54F8E5C53F4A32B'))

if __name__ == '__main__':
    unittest.main()
