from common import *

from apps.common.paths import HARDENED

if not utils.BITCOIN_ONLY:
    from apps.tezos.sign_tx import _get_address_from_contract
    from apps.tezos.helpers import validate_full_path
    from trezor.messages import TezosContractType
    from trezor.messages.TezosContractID import TezosContractID


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestTezosAddress(unittest.TestCase):
    def test_get_address_from_contract(self):
        contracts = [
            TezosContractID(
                tag=TezosContractType.Implicit,
                hash=unhexlify("0090ec585b4d5fa39b20213e46b232cc57a4cfab4b"),
            ),
            TezosContractID(
                tag=TezosContractType.Implicit,
                hash=unhexlify("017dfb3fef44082eca8cd3eccebd77db44633ffc9e"),
            ),
            TezosContractID(
                tag=TezosContractType.Implicit,
                hash=unhexlify("02c1fc1b7e503825068ff4fe2f8916f98af981eab1"),
            ),
            TezosContractID(
                tag=TezosContractType.Originated,
                hash=unhexlify("65671dedc69669f066f45d586a2ecdeddacc95af00"),
            ),
        ]

        outputs = [
            "tz1YrK8Hqt6GAPYRHAaeJmhETYyPSQCHTrkj",
            "tz2KoN7TFjhp96V2XikqYSGyDmVVUHXvkzko",
            "tz3e1k3QzCwEbRZrfHCwT3Npvw1rezmMQArY",
            "KT1HpwLq2AjZgEQspiSnYmdtaHy4NgXw6BDC",
        ]

        for i, contract in enumerate(contracts):
            self.assertEqual(_get_address_from_contract(contract), outputs[i])

    def test_paths(self):
        # 44'/1729'/a' is correct
        incorrect_paths = [
            [44 | HARDENED],
            [44 | HARDENED, 1729 | HARDENED],
            [44 | HARDENED, 1729 | HARDENED, 0],
            [44 | HARDENED, 1729 | HARDENED, 0 | HARDENED, 0],
            [44 | HARDENED, 1729 | HARDENED, 0 | HARDENED, 0 | HARDENED, 0 | HARDENED],
            [44 | HARDENED, 1729 | HARDENED, 0 | HARDENED, 1, 0],
            [44 | HARDENED, 1729 | HARDENED, 0 | HARDENED, 0, 0],
            [44 | HARDENED, 1729 | HARDENED, 1 | HARDENED, 1 | HARDENED],
            [44 | HARDENED, 1729 | HARDENED, 9999000 | HARDENED],
            [44 | HARDENED, 60 | HARDENED, 0 | HARDENED, 0, 0],
            [1 | HARDENED, 1 | HARDENED, 1 | HARDENED],
        ]
        correct_paths = [
            [44 | HARDENED, 1729 | HARDENED, 0 | HARDENED],
            [44 | HARDENED, 1729 | HARDENED, 3 | HARDENED],
            [44 | HARDENED, 1729 | HARDENED, 9 | HARDENED],
            [44 | HARDENED, 1729 | HARDENED, 0 | HARDENED, 0 | HARDENED],
            [44 | HARDENED, 1729 | HARDENED, 0 | HARDENED, 3 | HARDENED],
            [44 | HARDENED, 1729 | HARDENED, 0 | HARDENED, 9 | HARDENED],
        ]

        for path in incorrect_paths:
            self.assertFalse(validate_full_path(path))

        for path in correct_paths:
            self.assertTrue(validate_full_path(path))


if __name__ == "__main__":
    unittest.main()
