# flake8: noqa: F403,F405
from common import *  # isort:skip

import typing as t
import unittest

from trezor import utils, wire

if not utils.BITCOIN_ONLY:

    from ethereum_common import *
    from trezor.messages import EthereumNetworkInfo, EthereumTokenInfo

    from apps.ethereum import networks, tokens
    from apps.ethereum.definitions import Definitions

    TETHER_ADDRESS = b"\xda\xc1\x7f\x95\x8d\x2e\xe5\x23\xa2\x20\x62\x06\x99\x45\x97\xc1\x3d\x83\x1e\xc7"


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestEthereumDefinitions(unittest.TestCase):
    def assertUnknown(self, what: t.Any) -> None:
        if what is networks.UNKNOWN_NETWORK:
            return
        if what is tokens.UNKNOWN_TOKEN:
            return
        self.fail(f"Expected UNKNOWN_*, got {what}")

    def assertKnown(self, what: t.Any) -> None:
        if not EthereumNetworkInfo.is_type_of(
            what
        ) and not EthereumTokenInfo.is_type_of(what):
            self.fail(f"Expected network / token info, got {what}")
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
        network = make_eth_network(chain_id=42)
        defs = Definitions.from_encoded(encode_eth_network(network), None, chain_id=42)
        self.assertEqual(defs.network, network)
        self.assertUnknown(defs.get_token(b"\x00" * 20))

        token = make_eth_token(chain_id=42, address=b"\x00" * 20)
        defs = Definitions.from_encoded(
            encode_eth_network(network), encode_eth_token(token), chain_id=42
        )
        self.assertEqual(defs.network, network)
        self.assertEqual(defs.get_token(b"\x00" * 20), token)

        token = make_eth_token(chain_id=1, address=b"\x00" * 20)
        defs = Definitions.from_encoded(None, encode_eth_token(token), chain_id=1)
        self.assertKnown(defs.network)
        self.assertEqual(defs.get_token(b"\x00" * 20), token)

    def test_external_token_mismatch(self) -> None:
        network = make_eth_network(chain_id=42)
        token = make_eth_token(chain_id=43, address=b"\x00" * 20)
        defs = Definitions.from_encoded(
            encode_eth_network(network), encode_eth_token(token)
        )
        self.assertUnknown(defs.get_token(b"\x00" * 20))

    def test_external_chain_match(self) -> None:
        network = make_eth_network(chain_id=42)
        token = make_eth_token(chain_id=42, address=b"\x00" * 20)
        defs = Definitions.from_encoded(
            encode_eth_network(network), encode_eth_token(token), chain_id=42
        )
        self.assertEqual(defs.network, network)
        self.assertEqual(defs.get_token(b"\x00" * 20), token)

        with self.assertRaises(wire.DataError):
            Definitions.from_encoded(
                encode_eth_network(network), encode_eth_token(token), chain_id=333
            )

    def test_external_slip44_mismatch(self) -> None:
        network = make_eth_network(chain_id=42, slip44=1999)
        token = make_eth_token(chain_id=42, address=b"\x00" * 20)
        defs = Definitions.from_encoded(
            encode_eth_network(network), encode_eth_token(token), slip44=1999
        )
        self.assertEqual(defs.network, network)
        self.assertEqual(defs.get_token(b"\x00" * 20), token)

        with self.assertRaises(wire.DataError):
            Definitions.from_encoded(
                encode_eth_network(network), encode_eth_token(token), slip44=333
            )

    def test_ignore_encoded_network(self) -> None:
        # when network is builtin, ignore the encoded one
        network = encode_eth_network(chain_id=1, symbol="BAD")
        defs = Definitions.from_encoded(network, None, chain_id=1)
        self.assertNotEqual(defs.network, network)

    def test_ignore_encoded_token(self) -> None:
        # when token is builtin, ignore the encoded one
        token = encode_eth_token(chain_id=1, address=TETHER_ADDRESS, symbol="BAD")
        defs = Definitions.from_encoded(None, token, chain_id=1)
        self.assertNotEqual(defs.get_token(TETHER_ADDRESS), token)

    def test_ignore_with_no_match(self) -> None:
        network = encode_eth_network(chain_id=100_000, symbol="BAD")
        # smoke test: definition is accepted
        defs = Definitions.from_encoded(network, None, chain_id=100_000)
        self.assertKnown(defs.network)

        # same definition but nothing to match it to
        defs = Definitions.from_encoded(network, None)
        self.assertUnknown(defs.network)


if __name__ == "__main__":
    unittest.main()
