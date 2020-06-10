from common import *
from storage import cache
from trezor import wire
from trezor.crypto import bip39
from apps.common.paths import HARDENED

if not utils.BITCOIN_ONLY:
    from apps.ethereum.keychain import (
        from_address_n,
        with_keychain_from_path,
        with_keychain_from_chain_id,
    )
    from apps.ethereum.networks import by_chain_id, by_slip44

    from trezor.messages.EthereumGetAddress import EthereumGetAddress
    from trezor.messages.EthereumSignTx import EthereumSignTx


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestEthereumKeychain(unittest.TestCase):
    def _check_keychain(self, keychain, slip44_id):
        # valid address should succeed
        valid_addresses = (
            [44 | HARDENED, slip44_id | HARDENED],
            [44 | HARDENED, slip44_id | HARDENED, 0 | HARDENED],
            [44 | HARDENED, slip44_id | HARDENED, 19 | HARDENED],
            [44 | HARDENED, slip44_id | HARDENED, 0 | HARDENED, 0, 0],
        )
        for addr in valid_addresses:
            keychain.derive(addr)
        # invalid address should fail
        invalid_addresses = (
            [44 | HARDENED],
            [44 | HARDENED, 0 | HARDENED],
            [42 | HARDENED, slip44_id | HARDENED],
            [0 | HARDENED, slip44_id | HARDENED, 0 | HARDENED],
        )
        for addr in invalid_addresses:
            self.assertRaises(
                wire.DataError, keychain.derive, addr,
            )

    def setUp(self):
        cache.start_session()
        seed = bip39.seed(" ".join(["all"] * 12), "")
        cache.set(cache.APP_COMMON_SEED, seed)

    def test_from_address_n(self):
        # valid keychain m/44'/60'/0'
        keychain = await_result(
            from_address_n(
                wire.DUMMY_CONTEXT, [44 | HARDENED, 60 | HARDENED, 0 | HARDENED]
            )
        )
        self._check_keychain(keychain, 60)

    def test_from_address_n_unknown(self):
        # try Bitcoin slip44 id m/44'/0'/0'
        with self.assertRaises(wire.DataError):
            await_result(
                from_address_n(
                    wire.DUMMY_CONTEXT, [44 | HARDENED, 0 | HARDENED, 0 | HARDENED]
                )
            )

    def test_bad_address_n(self):
        # keychain generated from valid slip44 id but invalid address m/0'/60'/0'
        keychain = await_result(
            from_address_n(
                wire.DUMMY_CONTEXT, [0 | HARDENED, 60 | HARDENED, 0 | HARDENED]
            )
        )
        self._check_keychain(keychain, 60)

    def test_with_keychain_from_path(self):
        @with_keychain_from_path
        async def handler(ctx, msg, keychain):
            self._check_keychain(keychain, msg.address_n[1] & ~HARDENED)

        await_result(
            handler(
                wire.DUMMY_CONTEXT,
                EthereumGetAddress(
                    address_n=[44 | HARDENED, 60 | HARDENED, 0 | HARDENED]
                ),
            )
        )
        await_result(
            handler(
                wire.DUMMY_CONTEXT,
                EthereumGetAddress(
                    address_n=[44 | HARDENED, 108 | HARDENED, 0 | HARDENED]
                ),
            )
        )

        with self.assertRaises(wire.DataError):
            await_result(
                handler(
                    wire.DUMMY_CONTEXT,
                    EthereumGetAddress(
                        address_n=[44 | HARDENED, 0 | HARDENED, 0 | HARDENED]
                    ),
                )
            )

    def test_with_keychain_from_chain_id(self):
        @with_keychain_from_chain_id
        async def handler_chain_id(ctx, msg, keychain):
            network = by_chain_id(msg.chain_id)
            # standard tests
            self._check_keychain(keychain, network.slip44)
            # provided address should succeed too
            keychain.derive(msg.address_n)

        await_result(  # Ethereum
            handler_chain_id(
                wire.DUMMY_CONTEXT,
                EthereumSignTx(
                    address_n=[44 | HARDENED, 60 | HARDENED, 0 | HARDENED],
                    chain_id=1,
                ),
            )
        )

        await_result(  # Ethereum Classic
            handler_chain_id(
                wire.DUMMY_CONTEXT,
                EthereumSignTx(
                    address_n=[44 | HARDENED, 61 | HARDENED, 0 | HARDENED],
                    chain_id=61,
                ),
            )
        )

        with self.assertRaises(wire.DataError):
            await_result(  # unknown chain_id
                handler_chain_id(
                    wire.DUMMY_CONTEXT,
                    EthereumSignTx(
                        address_n=[44 | HARDENED, 60 | HARDENED, 0 | HARDENED],
                        chain_id=123456789,
                    ),
                )
            )

        with self.assertRaises(wire.DataError):
            await_result(  # chain_id and network mismatch
                handler_chain_id(
                    wire.DUMMY_CONTEXT,
                    EthereumSignTx(
                        address_n=[44 | HARDENED, 60 | HARDENED, 0 | HARDENED],
                        chain_id=2,
                    ),
                )
            )

    def test_missing_chain_id(self):
        @with_keychain_from_chain_id
        async def handler_chain_id(ctx, msg, keychain):
            network = by_slip44(msg.address_n[1] & ~HARDENED)
            # standard tests
            self._check_keychain(keychain, network.slip44)
            # provided address should succeed too
            keychain.derive(msg.address_n)

        await_result(  # Ethereum
            handler_chain_id(
                wire.DUMMY_CONTEXT,
                EthereumSignTx(
                    address_n=[44 | HARDENED, 60 | HARDENED, 0 | HARDENED],
                    chain_id=None,
                ),
            )
        )

        await_result(  # Ethereum Classic
            handler_chain_id(
                wire.DUMMY_CONTEXT,
                EthereumSignTx(
                    address_n=[44 | HARDENED, 61 | HARDENED, 0 | HARDENED],
                ),
            )
        )

        with self.assertRaises(wire.DataError):
            await_result(  # unknown slip44 id
                handler_chain_id(
                    wire.DUMMY_CONTEXT,
                    EthereumSignTx(
                        address_n=[44 | HARDENED, 0 | HARDENED, 0 | HARDENED],
                    ),
                )
            )

    def test_wanchain(self):
        @with_keychain_from_chain_id
        async def handler_wanchain(ctx, msg, keychain):
            self._check_keychain(keychain, 5718350)
            # provided address should succeed too
            keychain.derive(msg.address_n)

        await_result(
            handler_wanchain(
                wire.DUMMY_CONTEXT,
                EthereumSignTx(
                    address_n=[44 | HARDENED, 5718350 | HARDENED, 0 | HARDENED],
                    chain_id=3,
                    tx_type=6,
                ),
            )
        )


if __name__ == "__main__":
    unittest.main()
