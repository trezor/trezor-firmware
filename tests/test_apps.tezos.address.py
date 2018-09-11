from ubinascii import unhexlify

from common import *
from trezor.messages import TezosContractType
from trezor.messages.TezosContractID import TezosContractID

from apps.tezos.sign_tx import _get_address_from_contract


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


if __name__ == "__main__":
    unittest.main()
