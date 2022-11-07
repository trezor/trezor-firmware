from common import *
from storage import cache
from trezor import wire
from trezor.crypto import bip39
from apps.common.keychain import get_keychain
from apps.common.paths import HARDENED

if not utils.BITCOIN_ONLY:
    from apps.ethereum import CURVE, networks
    from apps.ethereum.keychain import (
        PATTERNS_ADDRESS,
        _schemas_from_address_n,
        with_keychain_and_network_from_path,
        with_keychain_and_defs_from_path,
        with_keychain_and_defs_from_chain_id,
    )

    from ethereum_common import (
        construct_network_info,
        get_encoded_network_definition,
        get_reference_ethereum_network_info,
    )

    from trezor.messages import (
        EthereumDefinitions,
        EthereumGetAddress,
        EthereumSignTypedData,
        EthereumSignTx,
    )


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
            [44 | HARDENED, slip44_id | HARDENED, 0 | HARDENED, 0 | HARDENED, 0 | HARDENED],
        )
        for addr in invalid_addresses:
            self.assertRaises(
                wire.DataError, keychain.derive, addr,
            )

    def setUp(self):
        cache.start_session()
        seed = bip39.seed(" ".join(["all"] * 12), "")
        cache.set(cache.APP_COMMON_SEED, seed)

    def from_address_n(self, address_n):
        schemas = _schemas_from_address_n(
            PATTERNS_ADDRESS,
            address_n,
            construct_network_info(0, address_n[1]),
        )
        return await_result(get_keychain(wire.DUMMY_CONTEXT, CURVE, schemas))

    def test_from_address_n(self):
        # valid keychain m/44'/60'/0'
        keychain = self.from_address_n([44 | HARDENED, 60 | HARDENED, 0 | HARDENED])
        self._check_keychain(keychain, 60)

    def test_from_address_n_ledger_live_legacy(self):
        # valid keychain m/44'/60'/0'/0
        keychain = self.from_address_n([44 | HARDENED, 60 | HARDENED, 0 | HARDENED, 0])
        self._check_keychain(keychain, 60)

    def test_from_address_n_unknown(self):
        # try Bitcoin slip44 id m/44'/0'/0'
        schemas = tuple(_schemas_from_address_n(
            PATTERNS_ADDRESS,
            [44 | HARDENED, 0 | HARDENED, 0 | HARDENED],
            networks.UNKNOWN_NETWORK,
        ))
        self.assertEqual(schemas, ())

    def test_bad_address_n(self):
        # keychain generated from valid slip44 id but invalid address m/0'/60'/0'
        keychain = self.from_address_n([0 | HARDENED, 60 | HARDENED, 0 | HARDENED])
        self._check_keychain(keychain, 60)

    def test_with_keychain_and_network_from_path(self):
        @with_keychain_and_network_from_path(*PATTERNS_ADDRESS)
        async def handler(ctx, msg, keychain, network):
            self._check_keychain(keychain, msg.address_n[1] & ~HARDENED)

        await_result(
            handler(
                wire.DUMMY_CONTEXT,
                EthereumGetAddress(
                    address_n=[44 | HARDENED, 60 | HARDENED, 0 | HARDENED],
                    encoded_network=get_encoded_network_definition(get_reference_ethereum_network_info(slip44=60)),
                ),
            )
        )
        await_result(
            handler(
                wire.DUMMY_CONTEXT,
                EthereumGetAddress(
                    address_n=[44 | HARDENED, 108 | HARDENED, 0 | HARDENED],
                    encoded_network=get_encoded_network_definition(get_reference_ethereum_network_info(slip44=108)),
                ),
            )
        )

        with self.assertRaises(wire.DataError):
            await_result(
                handler(
                    wire.DUMMY_CONTEXT,
                    EthereumGetAddress(
                        address_n=[44 | HARDENED, 0 | HARDENED, 0 | HARDENED],
                        encoded_network=None,
                    ),
                )
            )

    def test_with_keychain_and_defs_from_path(self):
        @with_keychain_and_defs_from_path(*PATTERNS_ADDRESS)
        async def handler(ctx, msg, keychain, defs):
            self._check_keychain(keychain, msg.address_n[1] & ~HARDENED)

        await_result(
            handler(
                wire.DUMMY_CONTEXT,
                EthereumSignTypedData(
                    primary_type="",
                    address_n=[44 | HARDENED, 60 | HARDENED, 0 | HARDENED],
                    encoded_network=get_encoded_network_definition(get_reference_ethereum_network_info(slip44=60)),
                ),
            )
        )

        await_result(  # Ethereum from Ledger Live legacy path
            handler(
                wire.DUMMY_CONTEXT,
                EthereumGetAddress(
                    address_n=[44 | HARDENED, 60 | HARDENED, 0 | HARDENED, 0]
                ),
            )
        )

        await_result(
            handler(
                wire.DUMMY_CONTEXT,
                EthereumSignTypedData(
                    primary_type="",
                    address_n=[44 | HARDENED, 108 | HARDENED, 0 | HARDENED],
                    encoded_network=get_encoded_network_definition(get_reference_ethereum_network_info(slip44=108)),
                ),
            )
        )

        with self.assertRaises(wire.DataError):
            await_result(
                handler(
                    wire.DUMMY_CONTEXT,
                    EthereumSignTypedData(
                    primary_type="",
                        address_n=[44 | HARDENED, 0 | HARDENED, 0 | HARDENED],
                        encoded_network=None,
                    ),
                )
            )

    def test_with_keychain_from_chain_id_and_defs(self):
        @with_keychain_and_defs_from_chain_id
        async def handler_chain_id(ctx, msg, keychain, defs):
            slip44_id = msg.address_n[1] & ~HARDENED
            # standard tests
            self._check_keychain(keychain, slip44_id)
            # provided address should succeed too
            keychain.derive(msg.address_n)

        await_result(  # Ethereum
            handler_chain_id(
                wire.DUMMY_CONTEXT,
                EthereumSignTx(
                    address_n=[44 | HARDENED, 60 | HARDENED, 0 | HARDENED],
                    chain_id=1,
                    gas_price=b"",
                    gas_limit=b"",
                    definitions=EthereumDefinitions(
                        encoded_network=get_encoded_network_definition(get_reference_ethereum_network_info(chain_id=1)),
                        encoded_token=None,
                    ),
                ),
            )
        )

        await_result(  # Ethereum from Ledger Live legacy path
            handler_chain_id(
                wire.DUMMY_CONTEXT,
                EthereumSignTx(
                    address_n=[44 | HARDENED, 60 | HARDENED, 0 | HARDENED, 0],
                    chain_id=1,
                    gas_price=b"",
                    gas_limit=b"",
                ),
            )
        )

        await_result(  # Ethereum Classic
            handler_chain_id(
                wire.DUMMY_CONTEXT,
                EthereumSignTx(
                    address_n=[44 | HARDENED, 61 | HARDENED, 0 | HARDENED],
                    chain_id=61,
                    gas_price=b"",
                    gas_limit=b"",
                    definitions=EthereumDefinitions(
                        encoded_network=get_encoded_network_definition(get_reference_ethereum_network_info(chain_id=61)),
                        encoded_token=None,
                    ),
                ),
            )
        )

        # Known chain-ids are allowed to use Ethereum derivation paths too, as there is
        # no risk of replaying the transaction on the Ethereum chain
        await_result(  # ETH slip44 with ETC chain-id
            handler_chain_id(
                wire.DUMMY_CONTEXT,
                EthereumSignTx(
                    address_n=[44 | HARDENED, 60 | HARDENED, 0 | HARDENED],
                    chain_id=61,
                    gas_price=b"",
                    gas_limit=b"",
                    definitions=EthereumDefinitions(
                        encoded_network=get_encoded_network_definition(get_reference_ethereum_network_info(chain_id=61)),
                        encoded_token=None,
                    ),
                ),
            )
        )

        with self.assertRaises(wire.DataError):
            await_result(  # chain_id and network mismatch
                handler_chain_id(
                    wire.DUMMY_CONTEXT,
                    EthereumSignTx(
                        address_n=[44 | HARDENED, 61 | HARDENED, 0 | HARDENED],
                        chain_id=2,
                        gas_price=b"",
                        gas_limit=b"",
                        definitions=EthereumDefinitions(
                            encoded_network=get_encoded_network_definition(get_reference_ethereum_network_info(chain_id=2)),
                            encoded_token=None,
                        ),
                    ),
                )
            )

if __name__ == "__main__":
    unittest.main()
