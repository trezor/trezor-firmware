from common import *
from apps.common.paths import HARDENED
from apps.stellar.helpers import address_from_public_key, public_key_from_address, validate_full_path
from trezor.wire import ProcessError


class TestStellarAddress(unittest.TestCase):

    def test_address_to_pubkey(self):
        self.assertEqual(public_key_from_address('GBOVKZBEM2YYLOCDCUXJ4IMRKHN4LCJAE7WEAEA2KF562XFAGDBOB64V'),
                         unhexlify('5d55642466b185b843152e9e219151dbc5892027ec40101a517bed5ca030c2e0'))

        self.assertEqual(public_key_from_address('GCN2K2HG53AWX2SP5UHRPMJUUHLJF2XBTGSXROTPWRGAYJCDDP63J2U6'),
                         unhexlify('9ba568e6eec16bea4fed0f17b134a1d692eae199a578ba6fb44c0c24431bfdb4'))

    def test_pubkey_to_address(self):
        addr = address_from_public_key(unhexlify('5d55642466b185b843152e9e219151dbc5892027ec40101a517bed5ca030c2e0'))
        self.assertEqual(addr, 'GBOVKZBEM2YYLOCDCUXJ4IMRKHN4LCJAE7WEAEA2KF562XFAGDBOB64V')

        addr = address_from_public_key(unhexlify('9ba568e6eec16bea4fed0f17b134a1d692eae199a578ba6fb44c0c24431bfdb4'))
        self.assertEqual(addr, 'GCN2K2HG53AWX2SP5UHRPMJUUHLJF2XBTGSXROTPWRGAYJCDDP63J2U6')

    def test_both(self):
        pubkey = unhexlify('dfcc77d08588601702e02de2dc603f5c5281bea23baa894ae3b3b4778e5bbe40')
        self.assertEqual(public_key_from_address(address_from_public_key(pubkey)), pubkey)

        pubkey = unhexlify('53214e6155469c32fb882b1b1d94930d5445a78202867b7ddc6a33ad42ff4464')
        self.assertEqual(public_key_from_address(address_from_public_key(pubkey)), pubkey)

        pubkey = unhexlify('5ed4690134e5ef79b290ea1e7a4b8f3b6b3bcf287463c18bfe36baa030e7efbd')
        self.assertEqual(public_key_from_address(address_from_public_key(pubkey)), pubkey)

    def test_invalid_address(self):
        with self.assertRaises(ProcessError):
            public_key_from_address('GCN2K2HG53AWX2SP5UHRPMJUUHLJF2XBTGSXROTPWRGAYJCDDP63J2AA')  # invalid checksum

    def test_paths(self):
        # 44'/148'/a' is correct
        incorrect_paths = [
            [44 | HARDENED],
            [44 | HARDENED, 148 | HARDENED],
            [44 | HARDENED, 148 | HARDENED, 0],
            [44 | HARDENED, 148 | HARDENED, 0 | HARDENED, 0 | HARDENED],
            [44 | HARDENED, 148 | HARDENED, 0 | HARDENED, 0 | HARDENED, 0 | HARDENED],
            [44 | HARDENED, 148 | HARDENED, 0 | HARDENED, 1, 0],
            [44 | HARDENED, 148 | HARDENED, 0 | HARDENED, 0, 0],
            [44 | HARDENED, 148 | HARDENED, 9999000 | HARDENED],
            [44 | HARDENED, 60 | HARDENED, 0 | HARDENED, 0, 0],
            [1 | HARDENED, 1 | HARDENED, 1 | HARDENED],
        ]
        correct_paths = [
            [44 | HARDENED, 148 | HARDENED, 0 | HARDENED],
            [44 | HARDENED, 148 | HARDENED, 3 | HARDENED],
            [44 | HARDENED, 148 | HARDENED, 9 | HARDENED],
        ]

        for path in incorrect_paths:
            self.assertFalse(validate_full_path(path))

        for path in correct_paths:
            self.assertTrue(validate_full_path(path))


if __name__ == '__main__':
    unittest.main()
