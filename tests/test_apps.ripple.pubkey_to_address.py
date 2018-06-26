from common import *
from apps.ripple.helpers import address_from_public_key


class TestStellarPubkeyToAddress(unittest.TestCase):

    def test_pubkey_to_address(self):
        addr = address_from_public_key(unhexlify('ed9434799226374926eda3b54b1b461b4abf7237962eae18528fea67595397fa32'))
        self.assertEqual(addr, 'rDTXLQ7ZKZVKz33zJbHjgVShjsBnqMBhmN')

        addr = address_from_public_key(unhexlify('03e2b079e9b09ae8916da8f5ee40cbda9578dbe7c820553fe4d5f872eec7b1fdd4'))
        self.assertEqual(addr, 'rhq549rEtUrJowuxQC2WsHNGLjAjBQdAe8')

        addr = address_from_public_key(unhexlify('0282ee731039929e97db6aec242002e9aa62cd62b989136df231f4bb9b8b7c7eb2'))
        self.assertEqual(addr, 'rKzE5DTyF9G6z7k7j27T2xEas2eMo85kmw')


if __name__ == '__main__':
    unittest.main()
