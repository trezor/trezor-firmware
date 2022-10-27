from common import *
from trezor import wire
from ubinascii import hexlify  # noqa: F401

if not utils.BITCOIN_ONLY:
    import apps.ethereum.definitions as dfs

    from apps.ethereum import networks, tokens
    from ethereum_common import *
    from trezor import protobuf
    from trezor.messages import (
        EthereumDefinitions,
        EthereumNetworkInfo,
        EthereumTokenInfo,
        EthereumGetAddress,
        EthereumGetPublicKey,
        EthereumSignMessage,
        EthereumSignTx,
        EthereumSignTxEIP1559,
        EthereumSignTypedData,
        EthereumVerifyMessage,
    )

@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestDecodeDefinition(unittest.TestCase):
    def test_short_message(self):
        with self.assertRaises(wire.DataError):
            dfs.decode_definition(b'\x00', EthereumNetworkInfo)
        with self.assertRaises(wire.DataError):
            dfs.decode_definition(b'\x00', EthereumTokenInfo)

    # successful decode network
    def test_network_definition(self):
        ubiq_network_encoded = get_encoded_network_definition(8)
        ubiq_network = get_reference_ethereum_network_info(8)
        self.assertEqual(dfs.decode_definition(ubiq_network_encoded, EthereumNetworkInfo), ubiq_network)

    # successful decode token
    def test_token_definition(self):
        # Sphere Token
        sphr_token_encoded = get_encoded_token_definition(8, "20e3dd746ddf519b23ffbbb6da7a5d33ea6349d6")
        sphr_token = get_reference_ethereum_token_info(8, "20e3dd746ddf519b23ffbbb6da7a5d33ea6349d6")
        self.assertEqual(dfs.decode_definition(sphr_token_encoded, EthereumTokenInfo), sphr_token)

    def test_invalid_data(self):
        ubiq_network_encoded = get_encoded_network_definition(8)

        invalid_dataset = []

        # mangle Merkle tree proof
        invalid_dataset.append(bytearray(ubiq_network_encoded))
        invalid_dataset[-1][-65] += 1

        # mangle signature
        invalid_dataset.append(bytearray(ubiq_network_encoded))
        invalid_dataset[-1][-1] += 1

        # mangle payload
        invalid_dataset.append(bytearray(ubiq_network_encoded))
        invalid_dataset[-1][16] += 1

        # wrong format version
        invalid_dataset.append(bytearray(ubiq_network_encoded))
        invalid_dataset[-1][:5] = b'trzd2' # change "trzd1" to "trzd2"

        # wrong definition type
        invalid_dataset.append(bytearray(ubiq_network_encoded))
        invalid_dataset[-1][8] += 1

        # wrong data format version
        invalid_dataset.append(bytearray(ubiq_network_encoded))
        invalid_dataset[-1][13] += 1

        for data in invalid_dataset:
            with self.assertRaises(wire.DataError):
                dfs.decode_definition(bytes(data), EthereumNetworkInfo)

    def test_wrong_requested_type(self):
        ubiq_network_encoded = get_encoded_network_definition(8)
        with self.assertRaises(wire.DataError):
            dfs.decode_definition(ubiq_network_encoded, EthereumTokenInfo)


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestGetAndCheckDefinition(unittest.TestCase):
    def test_get_network_definition(self):
        eth_network_encoded = get_encoded_network_definition(1)
        eth_network = get_reference_ethereum_network_info(1)
        self.assertEqual(dfs.get_and_check_definition(eth_network_encoded, EthereumNetworkInfo, 1), eth_network)
        self.assertEqual(dfs.get_and_check_definition(eth_network_encoded, EthereumNetworkInfo), eth_network)

    def test_get_token_definition(self):
        aave_token_encoded = get_encoded_token_definition(1, "7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9")
        aave_token = get_reference_ethereum_token_info(1, "7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9")
        self.assertEqual(dfs.get_and_check_definition(aave_token_encoded, EthereumTokenInfo, 1), aave_token)
        self.assertEqual(dfs.get_and_check_definition(aave_token_encoded, EthereumTokenInfo), aave_token)

    def test_invalid_expected_type(self):
        ubiq_network_encoded = get_encoded_network_definition(8)
        with self.assertRaises(wire.DataError):
            dfs.get_and_check_definition(ubiq_network_encoded, EthereumTokenInfo, 8)

        sphr_token_encoded = get_encoded_token_definition(8, "20e3dd746ddf519b23ffbbb6da7a5d33ea6349d6")
        with self.assertRaises(wire.DataError):
            dfs.get_and_check_definition(sphr_token_encoded, EthereumNetworkInfo, 8)

    def test_fail_check_chain_id(self):
        ubiq_network_encoded = get_encoded_network_definition(8)
        with self.assertRaises(wire.DataError):
            dfs.get_and_check_definition(ubiq_network_encoded, EthereumNetworkInfo, 1)

        sphr_token_encoded = get_encoded_token_definition(8, "20e3dd746ddf519b23ffbbb6da7a5d33ea6349d6")
        with self.assertRaises(wire.DataError):
            dfs.get_and_check_definition(sphr_token_encoded, EthereumTokenInfo, 1)

    def test_invalid_encoded_definition(self):
        ubiq_network_encoded = get_encoded_network_definition(8)
        definition = bytearray(ubiq_network_encoded)
        # mangle signature - this should have the same effect as it has in "decode_definition" function
        definition[-1] += 1
        with self.assertRaises(wire.DataError):
            dfs.get_and_check_definition(bytes(definition), EthereumNetworkInfo, 8)


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestEthereumDefinitions(unittest.TestCase):
    def get_and_compare_ethereum_definitions(
        self,
        network_definition: bytes | None,
        token_definition: bytes | None,
        ref_chain_id: int | None,
        ref_token_address: bytes,
        network_info: EthereumNetworkInfo,
        token_info: EthereumTokenInfo,
    ):
        # get
        definitions = dfs.Definitions(network_definition, token_definition, ref_chain_id)

        # compare
        self.assertEqual(definitions.network, network_info)
        self.assertEqual(definitions.get_token(ref_token_address), token_info)

    def test_get_definitions(self):
        # built-in
        eth_network = get_reference_ethereum_network_info(1)
        aave_token = get_reference_ethereum_token_info(1, "7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9")
        # not built-in
        ubiq_network_encoded = get_encoded_network_definition(8)
        ubiq_network = get_reference_ethereum_network_info(8)
        sphr_token_encoded = get_encoded_token_definition(8, "20e3dd746ddf519b23ffbbb6da7a5d33ea6349d6")
        sphr_token = get_reference_ethereum_token_info(8, "20e3dd746ddf519b23ffbbb6da7a5d33ea6349d6")

        calls_params = [
            # no network
            (None, None, None, aave_token.address, networks.UNKNOWN_NETWORK, tokens.UNKNOWN_TOKEN),

            # no encoded definitions
            (None, None, eth_network.chain_id, aave_token.address, eth_network, aave_token),

            # no encoded definitions - token address from other chain
            (None, None, eth_network.chain_id, sphr_token.address, eth_network, tokens.UNKNOWN_TOKEN),

            # with encoded network definition
            (ubiq_network_encoded, None, None, aave_token.address, ubiq_network, tokens.UNKNOWN_TOKEN),
            (ubiq_network_encoded, None, None, sphr_token.address, ubiq_network, tokens.UNKNOWN_TOKEN),
            (ubiq_network_encoded, None, eth_network.chain_id, aave_token.address, eth_network, aave_token),
            (ubiq_network_encoded, None, ubiq_network.chain_id, sphr_token.address, ubiq_network, tokens.UNKNOWN_TOKEN),

            # with encoded network definition - token address from other chain
            (ubiq_network_encoded, None, eth_network.chain_id, sphr_token.address, eth_network, tokens.UNKNOWN_TOKEN),

            # with encoded network and token definition
            (ubiq_network_encoded, sphr_token_encoded, None, sphr_token.address, ubiq_network, sphr_token),
            (ubiq_network_encoded, sphr_token_encoded, ubiq_network.chain_id, sphr_token.address, ubiq_network, sphr_token),

            # with encoded network and token definition - token address from other chain
            (ubiq_network_encoded, sphr_token_encoded, None, aave_token.address, ubiq_network, tokens.UNKNOWN_TOKEN),
            (ubiq_network_encoded, sphr_token_encoded, ubiq_network.chain_id, aave_token.address, ubiq_network, tokens.UNKNOWN_TOKEN),
        ]
        for params in calls_params:
            self.get_and_compare_ethereum_definitions(*params)

    def test_get_definitions_chain_id_mismatch(self):
        # built-in
        eth_network_encoded = get_encoded_network_definition(1)
        eth_network = get_reference_ethereum_network_info(1)
        aave_token_encoded = get_encoded_token_definition(1, "7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9")
        # not built-in
        ubiq_network_encoded = get_encoded_network_definition(8)
        ubiq_network = get_reference_ethereum_network_info(8)
        sphr_token_encoded = get_encoded_token_definition(8, "20e3dd746ddf519b23ffbbb6da7a5d33ea6349d6")

        # these variations should have the same result - error on chain id check in encoded definition
        calls_params = [
            (None, sphr_token_encoded, None),
            (None, aave_token_encoded, None),
            (None, sphr_token_encoded, eth_network.chain_id),
            (None, aave_token_encoded, ubiq_network.chain_id),
            (eth_network_encoded, None, ubiq_network.chain_id),
            (ubiq_network_encoded, sphr_token_encoded, eth_network.chain_id),
            (eth_network_encoded, aave_token_encoded, ubiq_network.chain_id),
        ]
        for params in calls_params:
            with self.assertRaises(wire.DataError):
                dfs.Definitions(*params)


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestGetDefinitonsFromMsg(unittest.TestCase):
    def get_and_compare_ethereum_definitions(
        self,
        msg: protobuf.MessageType,
        network_info: EthereumNetworkInfo,
        token_info: EthereumTokenInfo,
        ref_token_address: bytes,
    ):
        # get
        definitions = dfs.get_definitions_from_msg(msg)

        # compare
        self.assertEqual(definitions.network, network_info)
        self.assertEqual(definitions.get_token(ref_token_address), token_info)

    def test_get_definitions_SignTx_messages(self):
        # built-in
        eth_network = get_reference_ethereum_network_info(1)
        aave_token = get_reference_ethereum_token_info(1, "7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9")
        # not built-in
        ubiq_network_encoded = get_encoded_network_definition(8)
        ubiq_network = get_reference_ethereum_network_info(8)
        sphr_token_encoded = get_encoded_token_definition(8, "20e3dd746ddf519b23ffbbb6da7a5d33ea6349d6")
        sphr_token = get_reference_ethereum_token_info(8, "20e3dd746ddf519b23ffbbb6da7a5d33ea6349d6")

        def create_EthereumSignTx_msg(**kwargs):
            return EthereumSignTx(
                gas_price=b'',
                gas_limit=b'',
                **kwargs
            )

        def create_EthereumSignTxEIP1559_msg(**kwargs):
            return EthereumSignTxEIP1559(
                nonce=b'',
                max_gas_fee=b'',
                max_priority_fee=b'',
                gas_limit=b'',
                value=b'',
                data_length=0,
                **kwargs
            )

        # both network and token should be loaded
        params_set = [
            (
                create_EthereumSignTx_msg(
                    chain_id=ubiq_network.chain_id,
                    to=hexlify(sphr_token.address),
                    definitions=EthereumDefinitions(
                        encoded_network=ubiq_network_encoded,
                        encoded_token=sphr_token_encoded,
                    ),
                ),
                ubiq_network,
                sphr_token,
                sphr_token.address,
            ),
            (
                create_EthereumSignTx_msg(
                    chain_id=eth_network.chain_id,
                    to=hexlify(aave_token.address),
                ),
                eth_network,
                aave_token,
                aave_token.address,
            ),
            (
                create_EthereumSignTxEIP1559_msg(
                    chain_id=ubiq_network.chain_id,
                    to=hexlify(sphr_token.address),
                    definitions=EthereumDefinitions(
                        encoded_network=ubiq_network_encoded,
                        encoded_token=sphr_token_encoded,
                    ),
                ),
                ubiq_network,
                sphr_token,
                sphr_token.address,
            ),
            (
                create_EthereumSignTxEIP1559_msg(
                    chain_id=eth_network.chain_id,
                    to=hexlify(aave_token.address),
                ),
                eth_network,
                aave_token,
                aave_token.address,
            ),
        ]
        for params in params_set:
            self.get_and_compare_ethereum_definitions(*params)

    def test_EthereumSignTypedData_message(self):
        ubiq_network_encoded = get_encoded_network_definition(8)
        ubiq_network = get_reference_ethereum_network_info(8)
        sphr_token = get_reference_ethereum_token_info(8, "20e3dd746ddf519b23ffbbb6da7a5d33ea6349d6")

        msg = EthereumSignTypedData(
            primary_type="",
            definitions=EthereumDefinitions(
                encoded_network=ubiq_network_encoded,
                encoded_token=None,
            )
        )

        self.get_and_compare_ethereum_definitions(msg, ubiq_network, tokens.UNKNOWN_TOKEN, sphr_token.address)

        # neither network nor token should be loaded
        msg = EthereumSignTypedData(primary_type="")
        self.get_and_compare_ethereum_definitions(msg, networks.UNKNOWN_NETWORK, tokens.UNKNOWN_TOKEN, sphr_token.address)

    def test_invalid_message(self):
        sphr_token = get_reference_ethereum_token_info(8, "20e3dd746ddf519b23ffbbb6da7a5d33ea6349d6")

        # msg without any of the required fields - chain_id, definitions, encoded_network
        class InvalidMsg():
            pass

        self.get_and_compare_ethereum_definitions(InvalidMsg(), networks.UNKNOWN_NETWORK, tokens.UNKNOWN_TOKEN, sphr_token.address)


if __name__ == "__main__":
    unittest.main()
