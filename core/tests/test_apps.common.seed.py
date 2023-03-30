from common import *

from apps.common.keychain import Keychain
from apps.common.seed import Slip21Node
from trezor import wire
from trezor.crypto import bip39

class TestSeed(unittest.TestCase):
    def test_slip21(self):
        seed = bip39.seed(' '.join(['all'] * 12), '')
        node1 = Slip21Node(seed)
        node2 = node1.clone()
        keychain = Keychain(seed, "", [], slip21_namespaces=[[b"SLIP-0021"]])

        # Key(m)
        KEY_M = unhexlify(b"dbf12b44133eaab506a740f6565cc117228cbf1dd70635cfa8ddfdc9af734756")
        self.assertEqual(node1.key(), KEY_M)

        # Key(m/"SLIP-0021")
        KEY_M_SLIP0021 = unhexlify(b"1d065e3ac1bbe5c7fad32cf2305f7d709dc070d672044a19e610c77cdf33de0d")
        node1.derive_path([b"SLIP-0021"])
        self.assertEqual(node1.key(), KEY_M_SLIP0021)
        self.assertEqual(keychain.derive_slip21([b"SLIP-0021"]).key(), KEY_M_SLIP0021)

        # Key(m/"SLIP-0021"/"Master encryption key")
        KEY_M_SLIP0021_MEK = unhexlify(b"ea163130e35bbafdf5ddee97a17b39cef2be4b4f390180d65b54cf05c6a82fde")
        node1.derive_path([b"Master encryption key"])
        self.assertEqual(node1.key(), KEY_M_SLIP0021_MEK)
        self.assertEqual(keychain.derive_slip21([b"SLIP-0021", b"Master encryption key"]).key(), KEY_M_SLIP0021_MEK)

        # Key(m/"SLIP-0021"/"Authentication key")
        KEY_M_SLIP0021_AK = unhexlify(b"47194e938ab24cc82bfa25f6486ed54bebe79c40ae2a5a32ea6db294d81861a6")
        node2.derive_path([b"SLIP-0021", b"Authentication key"])
        self.assertEqual(node2.key(), KEY_M_SLIP0021_AK)
        self.assertEqual(keychain.derive_slip21([b"SLIP-0021", b"Authentication key"]).key(), KEY_M_SLIP0021_AK)

        # Forbidden paths.
        with self.assertRaises(wire.DataError):
            keychain.derive_slip21([])
        with self.assertRaises(wire.DataError):
            keychain.derive_slip21([b"SLIP-9999", b"Authentication key"])


if __name__ == '__main__':
    unittest.main()
