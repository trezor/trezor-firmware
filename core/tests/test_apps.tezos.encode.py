from common import *

if not utils.BITCOIN_ONLY:
    from trezor.enums import TezosContractType
    from trezor.messages import TezosContractID
    from apps.tezos.helpers import base58_encode_check, write_bool, CONTRACT_ID_SIZE
    from apps.tezos.sign_tx import (
        write_uint8,
        write_bytes_fixed,
        _encode_data_with_bool_prefix,
        _encode_zarith,
        _encode_natural,
    )


# NOTE: copy-pasted from apps.tezos.sign_tx
def _encode_contract_id(w: "Writer", contract_id: TezosContractID) -> None:
    write_uint8(w, contract_id.tag)
    write_bytes_fixed(w, contract_id.hash, CONTRACT_ID_SIZE - 1)


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestTezosEncoding(unittest.TestCase):
    def test_tezos_encode_zarith(self):
        inputs = [2000000, 159066, 200, 60000, 157000000, 0]
        outputs = ["80897a", "dada09", "c801", "e0d403", "c0c2ee4a", "00"]

        for i, o in zip(inputs, outputs):
            w = bytearray()
            _encode_zarith(w, i)
            self.assertEqual(bytes(w), unhexlify(o))

    def test_tezos_encode_data_with_bool_prefix(self):
        w = bytearray()
        _encode_data_with_bool_prefix(w, None, 0)
        self.assertEqual(bytes(w), bytes([0]))

        data = "afffeb1dc3c0"
        w = bytearray()
        _encode_data_with_bool_prefix(w, unhexlify(data), 6)
        self.assertEqual(bytes(w), unhexlify("ff" + data))

    def test_tezos_encode_bool(self):
        w = bytearray()
        write_bool(w, True)
        self.assertEqual(bytes(w), bytes([255]))

        w = bytearray()
        write_bool(w, False)
        self.assertEqual(bytes(w), bytes([0]))

    def test_tezos_encode_contract_id(self):
        implicit = TezosContractID(
            tag=TezosContractType.Implicit,
            hash=unhexlify("00101368afffeb1dc3c089facbbe23f5c30b787ce9"),
        )
        w = bytearray()
        _encode_contract_id(w, implicit)
        self.assertEqual(
            bytes(w), unhexlify("0000101368afffeb1dc3c089facbbe23f5c30b787ce9")
        )

        originated = TezosContractID(
            tag=TezosContractType.Originated,
            hash=unhexlify("65671dedc69669f066f45d586a2ecdeddacc95af00"),
        )
        w = bytearray()
        _encode_contract_id(w, originated)
        self.assertEqual(
            bytes(w), unhexlify("0165671dedc69669f066f45d586a2ecdeddacc95af00")
        )

    def test_tezos_base58_encode_check(self):
        pkh = unhexlify("101368afffeb1dc3c089facbbe23f5c30b787ce9")

        self.assertEqual(
            base58_encode_check(pkh, prefix="tz1"),
            "tz1M72kkAJrntPtayM4yU4CCwQPLSdpEgRrn",
        )
        self.assertEqual(
            base58_encode_check(pkh, prefix="tz2"),
            "tz29nEixktH9p9XTFX7p8hATUyeLxXEz96KR",
        )
        self.assertEqual(
            base58_encode_check(pkh, prefix="tz3"),
            "tz3Mo3gHekQhCmykfnC58ecqJLXrjMKzkF2Q",
        )
        self.assertEqual(base58_encode_check(pkh), "2U14dJ6ED97bBHDZTQWA6umVL8SAVefXj")

    def test_tezos_encode_natural(self):
        inputs = [200000000000, 2000000, 159066, 200, 60000, 157000000, 0]
        outputs = ["0080c0ee8ed20b", "008092f401", "009ab513", "008803", "00a0a907", "008085dd9501", "0000"]

        for i, o in zip(inputs, outputs):
            w = bytearray()
            _encode_natural(w, i)
            self.assertEqual(bytes(w), unhexlify(o))


if __name__ == "__main__":
    unittest.main()
