# flake8: noqa: F403,F405
from common import *  # isort:skip

import unittest

from storage import cache_codec, cache_common
from trezor import wire
from trezor.crypto import bip39
from trezor.wire import context
from trezor.wire.codec.codec_context import CodecContext

from apps.common.keychain import get_keychain
from apps.common.paths import HARDENED

if not utils.BITCOIN_ONLY:
    from ethereum_common import encode_eth_network, make_eth_network
    from trezor.messages import (
        EthereumDefinitions,
        EthereumGetAddress,
        EthereumSignMessage,
        EthereumSignTx,
        EthereumSignTxEIP1559,
        EthereumSignTypedData,
    )

    from apps.ethereum import CURVE
    from apps.ethereum.keychain import (
        PATTERNS_ADDRESS,
        _defs_from_message,
        _schemas_from_network,
        _slip44_from_address_n,
        with_keychain_from_chain_id,
        with_keychain_from_path,
    )
    from apps.ethereum.networks import UNKNOWN_NETWORK


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestEthereumKeychain(unittest.TestCase):
    def _check_keychain(self, keychain, slip44_id):
        # valid address should succeed
        valid_addresses = (
            [44 | HARDENED, slip44_id | HARDENED, 0 | HARDENED],
            [44 | HARDENED, slip44_id | HARDENED, 19 | HARDENED],
            [44 | HARDENED, slip44_id | HARDENED, 0 | HARDENED, 0],
            [44 | HARDENED, slip44_id | HARDENED, 0 | HARDENED, 99],
            [44 | HARDENED, slip44_id | HARDENED, 0 | HARDENED, 0, 0],
            [44 | HARDENED, slip44_id | HARDENED, 0 | HARDENED, 0, 999],
        )
        for addr in valid_addresses:
            keychain.derive(addr)
        # invalid address should fail
        invalid_addresses = (
            [44 | HARDENED],
            [44 | HARDENED, slip44_id | HARDENED],
            [44 | HARDENED, 0 | HARDENED, 0 | HARDENED],
            [42 | HARDENED, slip44_id | HARDENED, 0 | HARDENED],
            [0 | HARDENED, slip44_id | HARDENED, 0 | HARDENED],
            [44 | HARDENED, 0 | HARDENED, 0 | HARDENED, 0],
            [44 | HARDENED, slip44_id | HARDENED, 1 | HARDENED, 0],
            [44 | HARDENED, slip44_id | HARDENED, 0 | HARDENED, 0 | HARDENED, 0],
            [
                44 | HARDENED,
                slip44_id | HARDENED,
                0 | HARDENED,
                0 | HARDENED,
                0 | HARDENED,
            ],
        )
        for addr in invalid_addresses:
            self.assertRaises(
                wire.DataError,
                keychain.derive,
                addr,
            )

    def setUpClass(self):
        context.CURRENT_CONTEXT = CodecContext(None, bytearray(64))

    def tearDownClass(self):
        context.CURRENT_CONTEXT = None

    def setUp(self):
        cache_codec.start_session()
        seed = bip39.seed(" ".join(["all"] * 12), "")
        cache_codec.get_active_session().set(cache_common.APP_COMMON_SEED, seed)

    def from_address_n(self, address_n):
        slip44 = _slip44_from_address_n(address_n)
        network = make_eth_network(slip44=slip44)
        schemas = _schemas_from_network(PATTERNS_ADDRESS, network)
        return await_result(get_keychain(CURVE, schemas))

    def test_from_address_n(self):
        # valid keychain m/44'/60'/0'
        keychain = self.from_address_n([44 | HARDENED, 60 | HARDENED, 0 | HARDENED])
        self._check_keychain(keychain, 60)

    def test_from_address_n_ledger_live_legacy(self):
        # valid keychain m/44'/60'/0'/0
        keychain = self.from_address_n([44 | HARDENED, 60 | HARDENED, 0 | HARDENED, 0])
        self._check_keychain(keychain, 60)

    def test_from_address_n_casa45(self):
        # valid keychain m/45'/60/0
        keychain = self.from_address_n([45 | HARDENED, 60, 0, 0, 0])
        keychain.derive([45 | HARDENED, 60, 0, 0, 0])
        with self.assertRaises(wire.DataError):
            keychain.derive([45 | HARDENED, 60 | HARDENED, 0, 0, 0])

    def test_with_keychain_from_path_short(self):
        # check that the keychain will not die when the address_n is too short
        @with_keychain_from_path(*PATTERNS_ADDRESS)
        async def handler(msg, keychain, defs):
            # in this case the network is unknown so the keychain should allow access
            # to Ethereum and testnet paths
            self._check_keychain(keychain, 60)
            self._check_keychain(keychain, 1)
            self.assertIs(defs.network, UNKNOWN_NETWORK)

        await_result(handler(EthereumGetAddress(address_n=[])))
        await_result(handler(EthereumGetAddress(address_n=[0])))

    def test_with_keychain_from_path_builtins(self):
        @with_keychain_from_path(*PATTERNS_ADDRESS)
        async def handler(msg, keychain, defs):
            slip44 = msg.address_n[1] & ~HARDENED
            self._check_keychain(keychain, slip44)
            self.assertEqual(defs.network.slip44, slip44)

        vectors = (
            # Ethereum
            [44 | HARDENED, 60 | HARDENED, 0 | HARDENED],
            # Ethereum from Ledger Live legacy path
            [44 | HARDENED, 60 | HARDENED, 0 | HARDENED, 0],
            # Ethereum Classic
            [44 | HARDENED, 61 | HARDENED, 0 | HARDENED],
        )

        for address_n in vectors:
            await_result(handler(EthereumGetAddress(address_n=address_n)))

        with self.assertRaises(wire.DataError):
            await_result(
                handler(  # unknown network
                    EthereumGetAddress(
                        address_n=[44 | HARDENED, 0 | HARDENED, 0 | HARDENED]
                    ),
                )
            )

    def test_with_keychain_from_path_external(self):
        FORBIDDEN_SYMBOL = "forbidden name"

        @with_keychain_from_path(*PATTERNS_ADDRESS)
        async def handler(msg, keychain, defs):
            slip44 = msg.address_n[1] & ~HARDENED
            self._check_keychain(keychain, slip44)
            self.assertEqual(defs.network.slip44, slip44)
            self.assertNotEqual(defs.network.name, FORBIDDEN_SYMBOL)

        vectors_valid = (  # slip44, network_def
            # invalid network is ignored when there is a builtin
            (60, b"hello"),
            # valid network is ignored when there is a builtin
            (60, encode_eth_network(slip44=60, symbol=FORBIDDEN_SYMBOL)),
            # valid network is accepted for unknown slip44 ids
            (33333, encode_eth_network(slip44=33333)),
        )

        for slip44, encoded_network in vectors_valid:
            await_result(
                handler(
                    EthereumGetAddress(
                        address_n=[44 | HARDENED, slip44 | HARDENED, 0 | HARDENED],
                        encoded_network=encoded_network,
                    ),
                )
            )

        vectors_invalid = (  # slip44, network_def
            # invalid network is rejected
            (30000, b"hello"),
            # invalid network does not prove mismatched slip44 id
            (30000, encode_eth_network(slip44=666)),
        )

        for slip44, encoded_network in vectors_invalid:
            with self.assertRaises(wire.DataError):
                await_result(
                    handler(
                        EthereumGetAddress(
                            address_n=[44 | HARDENED, slip44 | HARDENED, 0 | HARDENED],
                            encoded_network=encoded_network,
                        ),
                    )
                )

    def test_with_keychain_from_chain_id_builtin(self):
        @with_keychain_from_chain_id
        async def handler_chain_id(msg, keychain, defs):
            slip44_id = msg.address_n[1] & ~HARDENED
            # standard tests
            self._check_keychain(keychain, slip44_id)
            # provided address should succeed too
            keychain.derive(msg.address_n)
            self.assertEqual(defs.network.chain_id, msg.chain_id)

        vectors = (  # chain_id, address_n
            # Ethereum
            (1, [44 | HARDENED, 60 | HARDENED, 0 | HARDENED]),
            # Ethereum from Ledger Live legacy path
            (1, [44 | HARDENED, 60 | HARDENED, 0 | HARDENED, 0]),
            # Ethereum Classic
            (61, [44 | HARDENED, 61 | HARDENED, 0 | HARDENED]),
            # ETH slip44, ETC chain_id
            # (known networks are allowed to use eth slip44 for cross-signing)
            (61, [44 | HARDENED, 60 | HARDENED, 0 | HARDENED]),
        )

        for chain_id, address_n in vectors:
            await_result(  # Ethereum
                handler_chain_id(
                    EthereumSignTx(
                        address_n=address_n,
                        chain_id=chain_id,
                        gas_price=b"",
                        gas_limit=b"",
                    ),
                )
            )

        with self.assertRaises(wire.DataError):
            await_result(  # chain_id and network mismatch
                handler_chain_id(
                    EthereumSignTx(
                        address_n=[44 | HARDENED, 61 | HARDENED, 0 | HARDENED],
                        chain_id=2,
                        gas_price=b"",
                        gas_limit=b"",
                    ),
                )
            )

    def test_with_keychain_from_chain_id_external(self):
        FORBIDDEN_SYMBOL = "forbidden name"

        @with_keychain_from_chain_id
        async def handler_chain_id(msg, keychain, defs):
            slip44_id = msg.address_n[1] & ~HARDENED
            # standard tests
            self._check_keychain(keychain, slip44_id)
            # provided address should succeed too
            keychain.derive(msg.address_n)
            self.assertEqual(defs.network.chain_id, msg.chain_id)
            self.assertNotEqual(defs.network.name, FORBIDDEN_SYMBOL)

        vectors_valid = (  # chain_id, address_n, encoded_network
            # invalid network is ignored when there is a builtin
            (1, [44 | HARDENED, 60 | HARDENED, 0 | HARDENED], b"hello"),
            # valid network is ignored when there is a builtin
            (
                1,
                [44 | HARDENED, 60 | HARDENED, 0 | HARDENED],
                encode_eth_network(slip44=60, symbol=FORBIDDEN_SYMBOL),
            ),
            # valid network is accepted for unknown chain ids
            (
                33333,
                [44 | HARDENED, 33333 | HARDENED, 0 | HARDENED],
                encode_eth_network(slip44=33333, chain_id=33333),
            ),
            # valid network is allowed to cross-sign for Ethereum slip44
            (
                33333,
                [44 | HARDENED, 60 | HARDENED, 0 | HARDENED],
                encode_eth_network(slip44=33333, chain_id=33333),
            ),
            # valid network where slip44 and chain_id are different
            (
                44444,
                [44 | HARDENED, 33333 | HARDENED, 0 | HARDENED],
                encode_eth_network(slip44=33333, chain_id=44444),
            ),
        )

        for chain_id, address_n, encoded_network in vectors_valid:
            await_result(
                handler_chain_id(
                    EthereumSignTx(
                        address_n=address_n,
                        chain_id=chain_id,
                        gas_price=b"",
                        gas_limit=b"",
                        definitions=EthereumDefinitions(
                            encoded_network=encoded_network
                        ),
                    ),
                )
            )

        vectors_invalid = (  # chain_id, address_n, encoded_network
            # invalid network is rejected
            (30000, [44 | HARDENED, 30000 | HARDENED, 0 | HARDENED], b"hello"),
            # invalid network does not prove mismatched slip44 id
            (
                30000,
                [44 | HARDENED, 30000 | HARDENED, 0 | HARDENED],
                encode_eth_network(chain_id=30000, slip44=666),
            ),
            # invalid network does not prove mismatched chain_id
            (
                30000,
                [44 | HARDENED, 30000 | HARDENED, 0 | HARDENED],
                encode_eth_network(chain_id=666, slip44=30000),
            ),
        )

        for chain_id, address_n, encoded_network in vectors_invalid:
            with self.assertRaises(wire.DataError):
                await_result(
                    handler_chain_id(
                        EthereumSignTx(
                            address_n=address_n,
                            chain_id=chain_id,
                            gas_price=b"",
                            gas_limit=b"",
                            definitions=EthereumDefinitions(
                                encoded_network=encoded_network
                            ),
                        ),
                    )
                )

    def test_message_types(self) -> None:
        network = make_eth_network(symbol="Testing Network")
        encoded_network = encode_eth_network(network)

        messages = (
            EthereumSignTx(
                gas_price=b"",
                gas_limit=b"",
                chain_id=0,
                definitions=EthereumDefinitions(encoded_network=encoded_network),
            ),
            EthereumSignMessage(
                message=b"",
                encoded_network=encoded_network,
            ),
            EthereumSignTxEIP1559(
                chain_id=0,
                gas_limit=b"",
                max_gas_fee=b"",
                max_priority_fee=b"",
                nonce=b"",
                value=b"",
                data_length=0,
                definitions=EthereumDefinitions(encoded_network=encoded_network),
            ),
            EthereumSignTypedData(
                primary_type="",
                definitions=EthereumDefinitions(encoded_network=encoded_network),
            ),
            EthereumGetAddress(
                encoded_network=encoded_network,
            ),
        )

        for message in messages:
            defs = _defs_from_message(message, chain_id=0)
            self.assertEqual(defs.network, network)


if __name__ == "__main__":
    unittest.main()
