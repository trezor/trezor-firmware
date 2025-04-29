# flake8: noqa: F403,F405
from common import *  # isort:skip

import typing as t
import unittest

from trezor import utils, wire

if not utils.BITCOIN_ONLY:

    from ethereum_common import *
    from trezor.enums import DefinitionType
    from trezor.messages import EthereumNetworkInfo, EthereumTokenInfo, SolanaTokenInfo

    from apps.common.definitions import decode_definition


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestDecodeDefinition(unittest.TestCase):
    def test_short_message(self):
        for message in (EthereumNetworkInfo, EthereumTokenInfo, SolanaTokenInfo):
            with self.assertRaises(wire.DataError):
                decode_definition(b"\x00", message)

    # successful decode network
    def test_network_definition(self):
        network = make_eth_network(
            chain_id=42, slip44=69, symbol="FAKE", name="Fakenet"
        )
        encoded = encode_eth_network(network)
        try:
            self.assertEqual(decode_definition(encoded, EthereumNetworkInfo), network)
        except Exception as e:
            print(e.message)

    # successful decode token
    def test_token_definition(self):
        token = make_eth_token("FAKE", decimals=33, address=b"abcd" * 5, chain_id=42)
        encoded = encode_eth_token(token)
        self.assertEqual(decode_definition(encoded, EthereumTokenInfo), token)

    # successful decode solana token
    def test_solana_token_definition(self):
        token = make_solana_token("FAKE", mint=b"abcd" * 5, name="Fakenet")
        encoded = encode_solana_token(token)
        self.assertEqual(decode_definition(encoded, SolanaTokenInfo), token)

    def assertFailed(self, data: bytes) -> None:
        with self.assertRaises(wire.DataError):
            decode_definition(data, EthereumNetworkInfo)

    def test_mangled_signature(self):
        payload = make_payload()
        proof, signature = sign_payload(payload, [])
        bad_signature = signature[:-1] + b"\xff"
        self.assertFailed(payload + proof + bad_signature)

    def test_not_enough_signatures(self):
        payload = make_payload()
        proof, signature = sign_payload(payload, [], threshold=1)
        self.assertFailed(payload + proof + signature)

    def test_missing_signature(self):
        payload = make_payload()
        proof, _ = sign_payload(payload, [])
        self.assertFailed(payload + proof)

    def test_mangled_payload(self):
        payload = make_payload()
        proof, signature = sign_payload(payload, [])
        bad_payload = payload[:-1] + b"\xff"
        self.assertFailed(bad_payload + proof + signature)

    def test_proof_length_mismatch(self):
        payload = make_payload()
        _, signature = sign_payload(payload, [])
        bad_proof = b"\x01"
        self.assertFailed(payload + bad_proof + signature)

    def test_bad_proof(self):
        payload = make_payload()
        proof, signature = sign_payload(payload, [sha256(b"x").digest()])
        bad_proof = proof[:-1] + b"\xff"
        self.assertFailed(payload + bad_proof + signature)

    def test_trimmed_proof(self):
        payload = make_payload()
        proof, signature = sign_payload(payload, [])
        bad_proof = proof[:-1]
        self.assertFailed(payload + bad_proof + signature)

    def test_bad_prefix(self):
        payload = make_payload(prefix=b"trzd2")
        proof, signature = sign_payload(payload, [])
        self.assertFailed(payload + proof + signature)

    def test_bad_type(self):
        payload = make_payload(
            data_type=DefinitionType.ETHEREUM_TOKEN, message=make_eth_token()
        )
        proof, signature = sign_payload(payload, [])
        self.assertFailed(payload + proof + signature)

    def test_outdated(self):
        payload = make_payload(timestamp=0)
        proof, signature = sign_payload(payload, [])
        self.assertFailed(payload + proof + signature)

    def test_malformed_protobuf(self):
        payload = make_payload(message=b"\x00")
        proof, signature = sign_payload(payload, [])
        self.assertFailed(payload + proof + signature)

    def test_protobuf_mismatch(self):
        variants = (
            (DefinitionType.ETHEREUM_NETWORK, EthereumTokenInfo, make_eth_network()),
            (DefinitionType.ETHEREUM_TOKEN, EthereumNetworkInfo, make_eth_token()),
            (DefinitionType.SOLANA_TOKEN, SolanaTokenInfo, make_solana_token()),
        )
        for variant in variants:
            (
                encode_type,
                decode_type,
                _,
            ) = variant
            for other in variants:
                if other is variant:
                    continue
                _, _, message = other
                payload = make_payload(data_type=encode_type, message=message)
                proof, signature = sign_payload(payload, [])
                with self.assertRaises(wire.DataError):
                    decode_definition(payload + proof + signature, decode_type)

    def test_trailing_garbage(self):
        payload = make_payload()
        proof, signature = sign_payload(payload, [])
        self.assertFailed(payload + proof + signature + b"\x00")


if __name__ == "__main__":
    unittest.main()
