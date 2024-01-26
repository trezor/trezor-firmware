from common import *  # isort:skip

import typing as t
import unittest

from trezor import utils, wire

if not utils.BITCOIN_ONLY:

    from ethereum_common import *
    from trezor.enums import EthereumDefinitionType
    from trezor.messages import EthereumNetworkInfo, EthereumTokenInfo

    from apps.ethereum import networks, tokens
    from apps.ethereum.definitions import Definitions, decode_definition

    TETHER_ADDRESS = b"\xda\xc1\x7f\x95\x8d\x2e\xe5\x23\xa2\x20\x62\x06\x99\x45\x97\xc1\x3d\x83\x1e\xc7"


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestDecodeDefinition(unittest.TestCase):
    def test_short_message(self):
        with self.assertRaises(wire.DataError):
            decode_definition(b"\x00", EthereumNetworkInfo)
        with self.assertRaises(wire.DataError):
            decode_definition(b"\x00", EthereumTokenInfo)

    # successful decode network
    def test_network_definition(self):
        network = make_network(chain_id=42, slip44=69, symbol="FAKE", name="Fakenet")
        encoded = encode_network(network)
        try:
            self.assertEqual(decode_definition(encoded, EthereumNetworkInfo), network)
        except Exception as e:
            print(e.message)

    # successful decode token
    def test_token_definition(self):
        token = make_token("FAKE", decimals=33, address=b"abcd" * 5, chain_id=42)
        encoded = encode_token(token)
        self.assertEqual(decode_definition(encoded, EthereumTokenInfo), token)

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
        proof, signature = sign_payload(payload, [])
        self.assertFailed(payload + proof)

    def test_mangled_payload(self):
        payload = make_payload()
        proof, signature = sign_payload(payload, [])
        bad_payload = payload[:-1] + b"\xff"
        self.assertFailed(bad_payload + proof + signature)

    def test_proof_length_mismatch(self):
        payload = make_payload()
        proof, signature = sign_payload(payload, [])
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
            data_type=EthereumDefinitionType.TOKEN, message=make_token()
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
        payload = make_payload(
            data_type=EthereumDefinitionType.NETWORK, message=make_token()
        )
        proof, signature = sign_payload(payload, [])
        self.assertFailed(payload + proof + signature)

        payload = make_payload(
            data_type=EthereumDefinitionType.TOKEN, message=make_network()
        )
        proof, signature = sign_payload(payload, [])
        self.assertFailed(payload + proof + signature)

    def test_trailing_garbage(self):
        payload = make_payload()
        proof, signature = sign_payload(payload, [])
        self.assertFailed(payload + proof + signature + b"\x00")


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestEthereumDefinitions(unittest.TestCase):
    def assertUnknown(self, what: t.Any) -> None:
        if what is networks.UNKNOWN_NETWORK:
            return
        if what is tokens.UNKNOWN_TOKEN:
            return
        self.fail("Expected UNKNOWN_*, got %r" % what)

    def assertKnown(self, what: t.Any) -> None:
        if not EthereumNetworkInfo.is_type_of(
            what
        ) and not EthereumTokenInfo.is_type_of(what):
            self.fail("Expected network / token info, got %r" % what)
        if what is networks.UNKNOWN_NETWORK:
            self.fail("Expected known network, got UNKNOWN_NETWORK")
        if what is tokens.UNKNOWN_TOKEN:
            self.fail("Expected known token, got UNKNOWN_TOKEN")

    def test_empty(self) -> None:
        # no slip44 nor chain_id -- should short-circuit and always be unknown
        defs = Definitions.from_encoded(None, None)
        self.assertUnknown(defs.network)
        self.assertFalse(defs._tokens)
        self.assertUnknown(defs.get_token(TETHER_ADDRESS))

        # chain_id provided, no definition
        defs = Definitions.from_encoded(None, None, chain_id=100_000)
        self.assertUnknown(defs.network)
        self.assertFalse(defs._tokens)
        self.assertUnknown(defs.get_token(TETHER_ADDRESS))

    def test_builtin(self) -> None:
        defs = Definitions.from_encoded(None, None, chain_id=1)
        self.assertKnown(defs.network)
        self.assertFalse(defs._tokens)
        self.assertKnown(defs.get_token(TETHER_ADDRESS))
        self.assertUnknown(defs.get_token(b"\x00" * 20))

        defs = Definitions.from_encoded(None, None, slip44=60)
        self.assertKnown(defs.network)
        self.assertFalse(defs._tokens)
        self.assertKnown(defs.get_token(TETHER_ADDRESS))
        self.assertUnknown(defs.get_token(b"\x00" * 20))

    def test_external(self) -> None:
        network = make_network(chain_id=42)
        defs = Definitions.from_encoded(encode_network(network), None, chain_id=42)
        self.assertEqual(defs.network, network)
        self.assertUnknown(defs.get_token(b"\x00" * 20))

        token = make_token(chain_id=42, address=b"\x00" * 20)
        defs = Definitions.from_encoded(
            encode_network(network), encode_token(token), chain_id=42
        )
        self.assertEqual(defs.network, network)
        self.assertEqual(defs.get_token(b"\x00" * 20), token)

        token = make_token(chain_id=1, address=b"\x00" * 20)
        defs = Definitions.from_encoded(None, encode_token(token), chain_id=1)
        self.assertKnown(defs.network)
        self.assertEqual(defs.get_token(b"\x00" * 20), token)

    def test_external_token_mismatch(self) -> None:
        network = make_network(chain_id=42)
        token = make_token(chain_id=43, address=b"\x00" * 20)
        defs = Definitions.from_encoded(encode_network(network), encode_token(token))
        self.assertUnknown(defs.get_token(b"\x00" * 20))

    def test_external_chain_match(self) -> None:
        network = make_network(chain_id=42)
        token = make_token(chain_id=42, address=b"\x00" * 20)
        defs = Definitions.from_encoded(
            encode_network(network), encode_token(token), chain_id=42
        )
        self.assertEqual(defs.network, network)
        self.assertEqual(defs.get_token(b"\x00" * 20), token)

        with self.assertRaises(wire.DataError):
            Definitions.from_encoded(
                encode_network(network), encode_token(token), chain_id=333
            )

    def test_external_slip44_mismatch(self) -> None:
        network = make_network(chain_id=42, slip44=1999)
        token = make_token(chain_id=42, address=b"\x00" * 20)
        defs = Definitions.from_encoded(
            encode_network(network), encode_token(token), slip44=1999
        )
        self.assertEqual(defs.network, network)
        self.assertEqual(defs.get_token(b"\x00" * 20), token)

        with self.assertRaises(wire.DataError):
            Definitions.from_encoded(
                encode_network(network), encode_token(token), slip44=333
            )

    def test_ignore_encoded_network(self) -> None:
        # when network is builtin, ignore the encoded one
        network = encode_network(chain_id=1, symbol="BAD")
        defs = Definitions.from_encoded(network, None, chain_id=1)
        self.assertNotEqual(defs.network, network)

    def test_ignore_encoded_token(self) -> None:
        # when token is builtin, ignore the encoded one
        token = encode_token(chain_id=1, address=TETHER_ADDRESS, symbol="BAD")
        defs = Definitions.from_encoded(None, token, chain_id=1)
        self.assertNotEqual(defs.get_token(TETHER_ADDRESS), token)

    def test_ignore_with_no_match(self) -> None:
        network = encode_network(chain_id=100_000, symbol="BAD")
        # smoke test: definition is accepted
        defs = Definitions.from_encoded(network, None, chain_id=100_000)
        self.assertKnown(defs.network)

        # same definition but nothing to match it to
        defs = Definitions.from_encoded(network, None)
        self.assertUnknown(defs.network)


if __name__ == "__main__":
    unittest.main()
