from common import *
from ubinascii import unhexlify

from trezor.messages import TezosContractType
from trezor.messages.TezosContractID import TezosContractID

from apps.tezos.helpers import b58cencode, b58cdecode
from apps.tezos.sign_tx import (
    _encode_zarith,
    _encode_data_with_bool_prefix,
    _encode_bool,
    _encode_contract_id
)


class TestTezosEncoding(unittest.TestCase):

    def test_tezos_encode_zarith(self):
        inputs = [2000000, 159066, 200, 60000, 157000000, 0]
        outputs = ["80897a", "dada09", "c801", "e0d403", "c0c2ee4a", "00"]

        for i, o in zip(inputs, outputs):
            self.assertEqual(_encode_zarith(i), unhexlify(o))

    def test_tezos_encode_data_with_bool_prefix(self):
        self.assertEqual(_encode_data_with_bool_prefix(None), bytes([0]))

        data = "afffeb1dc3c0"
        self.assertEqual(_encode_data_with_bool_prefix(unhexlify(data)),
                         unhexlify("ff" + data))

    def test_tezos_encode_bool(self):
        self.assertEqual(_encode_bool(True), bytes([255]))
        self.assertEqual(_encode_bool(False), bytes([0]))

    def test_tezos_encode_contract_id(self):
        implicit = TezosContractID(
            tag=TezosContractType.Implicit,
            hash=unhexlify("00101368afffeb1dc3c089facbbe23f5c30b787ce9")
        )
        self.assertEqual(_encode_contract_id(implicit),
                         unhexlify("0000101368afffeb1dc3c089facbbe23f5c30b787ce9"))

        originated = TezosContractID(
            tag=TezosContractType.Originated,
            hash=unhexlify("65671dedc69669f066f45d586a2ecdeddacc95af00")
        )
        self.assertEqual(_encode_contract_id(originated),
                         unhexlify("0165671dedc69669f066f45d586a2ecdeddacc95af00"))

    def test_tezos_b58cencode(self):
        pkh = unhexlify("101368afffeb1dc3c089facbbe23f5c30b787ce9")

        self.assertEqual(b58cencode(pkh, prefix="tz1"),
                         "tz1M72kkAJrntPtayM4yU4CCwQPLSdpEgRrn")
        self.assertEqual(b58cencode(pkh, prefix="tz2"),
                         "tz29nEixktH9p9XTFX7p8hATUyeLxXEz96KR")
        self.assertEqual(b58cencode(pkh, prefix="tz3"),
                         "tz3Mo3gHekQhCmykfnC58ecqJLXrjMKzkF2Q")
        self.assertEqual(b58cencode(pkh), "2U14dJ6ED97bBHDZTQWA6umVL8SAVefXj")

    def test_tezos_b58cdecode(self):
        pkh = unhexlify("101368afffeb1dc3c089facbbe23f5c30b787ce9")

        address = "tz1M72kkAJrntPtayM4yU4CCwQPLSdpEgRrn"
        self.assertEqual(b58cdecode(address, prefix="tz1"), pkh)

        address = "tz29nEixktH9p9XTFX7p8hATUyeLxXEz96KR"
        self.assertEqual(b58cdecode(address, prefix="tz2"), pkh)

        address = "tz3Mo3gHekQhCmykfnC58ecqJLXrjMKzkF2Q"
        self.assertEqual(b58cdecode(address, prefix="tz3"), pkh)

        address = "2U14dJ6ED97bBHDZTQWA6umVL8SAVefXj"
        self.assertEqual(b58cdecode(address), pkh)


if __name__ == '__main__':
    unittest.main()
