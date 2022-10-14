from common import *
from trezor import wire
from ubinascii import hexlify  # noqa: F401

if not utils.BITCOIN_ONLY:
    import apps.ethereum.definitions as dfs

    from apps.ethereum import networks
    from ethereum_common import *
    from trezor import protobuf
    from trezor.enums import EthereumDefinitionType
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
class TestEthereumDefinitionParser(unittest.TestCase):
    def setUp(self):
        # prefix
        self.format_version = b'trzd1' + b'\x00' * 3
        self.definition_type = b'\x01'
        self.data_version = b'\x00\x00\x00\x02'
        self.payload_length_in_bytes = b'\x00\x03'
        self.prefix = self.format_version + self.definition_type + self.data_version + self.payload_length_in_bytes

        # payload
        self.payload = b'\x00\x00\x04' # optional length
        self.payload_with_prefix = self.prefix + self.payload

        # suffix - Merkle tree proof and signed root hash
        self.proof_length = b'\x01'
        self.proof = b'\x00' * 31 + b'\x06'
        self.signed_tree_root = b'\x00' * 63 + b'\x07'
        self.definition = self.payload_with_prefix + self.proof_length + self.proof + self.signed_tree_root

    def test_short_message(self):
        with self.assertRaises(wire.DataError):
            dfs.EthereumDefinitionParser(b'\x00')

    def test_ok_message(self):
        parser = dfs.EthereumDefinitionParser(self.definition)
        self.assertEqual(parser.format_version, self.format_version.rstrip(b'\0').decode("utf-8"))
        self.assertEqual(parser.definition_type, int.from_bytes(self.definition_type, 'big'))
        self.assertEqual(parser.data_version, int.from_bytes(self.data_version, 'big'))
        self.assertEqual(parser.payload_length_in_bytes, int.from_bytes(self.payload_length_in_bytes, 'big'))
        self.assertEqual(parser.payload, self.payload)
        self.assertEqual(parser.payload_with_prefix, self.payload_with_prefix)
        self.assertEqual(parser.proof_length, int.from_bytes(self.proof_length, 'big'))
        self.assertEqual(parser.proof, [self.proof])
        self.assertEqual(parser.signed_tree_root, self.signed_tree_root)


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestDecodeDefinition(unittest.TestCase):
    # successful decode network
    def test_network_definition(self):
        rinkeby_network = get_ethereum_network_info_with_definition(chain_id=4)
        self.assertEqual(dfs.decode_definition(rinkeby_network.definition, EthereumDefinitionType.NETWORK), rinkeby_network.info)

    # successful decode token
    def test_token_definition(self):
        # Karma Token
        kc_token = get_ethereum_token_info_with_definition(chain_id=4)
        self.assertEqual(dfs.decode_definition(kc_token.definition, EthereumDefinitionType.TOKEN), kc_token.info)

    def test_invalid_data(self):
        rinkeby_network = get_ethereum_network_info_with_definition(chain_id=4)

        invalid_dataset = []

        # mangle signature
        invalid_dataset.append(bytearray(rinkeby_network.definition))
        invalid_dataset[-1][-1] += 1

        # mangle payload
        invalid_dataset.append(bytearray(rinkeby_network.definition))
        invalid_dataset[-1][16] += 1

        # wrong format version
        invalid_dataset.append(bytearray(rinkeby_network.definition))
        invalid_dataset[-1][:5] = b'trzd2' # change "trzd1" to "trzd2"

        # wrong definition type
        invalid_dataset.append(bytearray(rinkeby_network.definition))
        invalid_dataset[-1][8] += 1

        # wrong data format version
        invalid_dataset.append(bytearray(rinkeby_network.definition))
        invalid_dataset[-1][13] += 1

        for data in invalid_dataset:
            with self.assertRaises(wire.DataError):
                dfs.decode_definition(bytes(data), EthereumDefinitionType.NETWORK)

    def test_wrong_requested_type(self):
        rinkeby_network = get_ethereum_network_info_with_definition(chain_id=4)
        with self.assertRaises(wire.DataError):
            dfs.decode_definition(rinkeby_network.definition, EthereumDefinitionType.TOKEN)


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestGetNetworkDefiniton(unittest.TestCase):
    def setUp(self):
        # use mockup function for built-in networks
        networks._networks_iterator = builtin_networks_iterator

    def test_get_network_definition(self):
        eth_network = get_ethereum_network_info_with_definition(chain_id=1)
        self.assertEqual(dfs._get_network_definiton(None, 1), eth_network.info)

    def test_built_in_preference(self):
        eth_network = get_ethereum_network_info_with_definition(chain_id=1)
        eth_classic_network = get_ethereum_network_info_with_definition(chain_id=61)
        self.assertEqual(dfs._get_network_definiton(eth_classic_network.definition, 1), eth_network.info)

    def test_no_built_in(self):
        ubiq_network = get_ethereum_network_info_with_definition(chain_id=8)

        # use provided (encoded) definition
        self.assertEqual(dfs._get_network_definiton(ubiq_network.definition, 8), ubiq_network.info)
        # here the result should be the same as above
        self.assertEqual(dfs._get_network_definiton(ubiq_network.definition, None), ubiq_network.info)
        # nothing should be found
        self.assertIsNone(dfs._get_network_definiton(None, 8))
        self.assertIsNone(dfs._get_network_definiton(None, None))

        # reference chain_id is used to check the encoded network chain_id - so in case they do not equal
        # error is raised
        with self.assertRaises(wire.DataError):
            dfs._get_network_definiton(ubiq_network.definition, ubiq_network.info.chain_id + 9999)

    def test_invalid_encoded_definition(self):
        rinkeby_network = get_ethereum_network_info_with_definition(chain_id=4)
        definition = bytearray(rinkeby_network.definition)
        # mangle signature - this should have the same effect as it has in "decode_definition" function
        definition[-1] += 1
        with self.assertRaises(wire.DataError):
            dfs._get_network_definiton(bytes(definition), None)


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestGetTokenDefiniton(unittest.TestCase):
    def setUp(self):
        # use mockup function for built-in tokens
        tokens.token_by_chain_address = builtin_token_by_chain_address

    def test_get_token_definition(self):
        aave_token = get_ethereum_token_info_with_definition(chain_id=1, token_address="7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9")
        self.assertEqual(dfs._get_token_definiton(None, aave_token.info.chain_id, aave_token.info.address), aave_token.info)

    def test_built_in_preference(self):
        aave_token = get_ethereum_token_info_with_definition(chain_id=1, token_address="7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9")
        taud_token = get_ethereum_token_info_with_definition(chain_id=1, token_address="00006100f7090010005f1bd7ae6122c3c2cf0090")
        self.assertEqual(dfs._get_token_definiton(taud_token.definition, aave_token.info.chain_id, aave_token.info.address), aave_token.info)

    def test_no_built_in(self):
        kc_token = get_ethereum_token_info_with_definition(chain_id=4)

        # use provided (encoded) definition
        self.assertEqual(dfs._get_token_definiton(kc_token.definition, kc_token.info.chain_id, kc_token.info.address), kc_token.info)
        # here the results should be the same as above
        self.assertEqual(dfs._get_token_definiton(kc_token.definition, None, kc_token.info.address), kc_token.info)
        self.assertEqual(dfs._get_token_definiton(kc_token.definition, kc_token.info.chain_id, None), kc_token.info)
        self.assertEqual(dfs._get_token_definiton(kc_token.definition, None, None), kc_token.info)
        # nothing should be found
        self.assertEqual(dfs._get_token_definiton(None, kc_token.info.chain_id, kc_token.info.address), tokens.UNKNOWN_TOKEN)
        self.assertEqual(dfs._get_token_definiton(None, None, kc_token.info.address), tokens.UNKNOWN_TOKEN)
        self.assertEqual(dfs._get_token_definiton(None, kc_token.info.chain_id, None), tokens.UNKNOWN_TOKEN)

        # reference chain_id and/or token address is used to check the encoded token chain_id/address - so in case they do not equal
        # tokens.UNKNOWN_TOKEN is returned
        self.assertEqual(dfs._get_token_definiton(kc_token.definition, kc_token.info.chain_id + 1, kc_token.info.address + b"\x00"), tokens.UNKNOWN_TOKEN)
        self.assertEqual(dfs._get_token_definiton(kc_token.definition, kc_token.info.chain_id, kc_token.info.address + b"\x00"), tokens.UNKNOWN_TOKEN)
        self.assertEqual(dfs._get_token_definiton(kc_token.definition, kc_token.info.chain_id + 1, kc_token.info.address), tokens.UNKNOWN_TOKEN)
        self.assertEqual(dfs._get_token_definiton(kc_token.definition, None, kc_token.info.address + b"\x00"), tokens.UNKNOWN_TOKEN)
        self.assertEqual(dfs._get_token_definiton(kc_token.definition, kc_token.info.chain_id + 1, None), tokens.UNKNOWN_TOKEN)

    def test_invalid_encoded_definition(self):
        kc_token = get_ethereum_token_info_with_definition(chain_id=4)
        definition = bytearray(kc_token.definition)
        # mangle signature - this should have the same effect as it has in "decode_definition" function
        definition[-1] += 1
        with self.assertRaises(wire.DataError):
            dfs._get_token_definiton(bytes(definition), None, None)


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestEthereumDefinitions(unittest.TestCase):
    def setUp(self):
        # use mockup functions for built-in definitions
        networks._networks_iterator = builtin_networks_iterator
        tokens.token_by_chain_address = builtin_token_by_chain_address

    def get_and_compare_ethereum_definitions(
        self,
        network_definition: bytes | None,
        token_definition: bytes | None,
        ref_chain_id: int | None,
        ref_token_address: bytes | None,
        network_info: EthereumNetworkInfo | None,
        token_info: EthereumTokenInfo | None,
    ):
        # get
        definitions = dfs.Definitions(network_definition, token_definition, ref_chain_id, ref_token_address)

        ref_token_dict = dict()
        if token_info is not None:
            ref_token_dict[token_info.address] = token_info

        # compare
        self.assertEqual(definitions.network, network_info)
        self.assertDictEqual(definitions.tokens, ref_token_dict)

    def test_get_definitions(self):
        # built-in
        eth_network = get_ethereum_network_info_with_definition(chain_id=1)
        aave_token = get_ethereum_token_info_with_definition(chain_id=1, token_address="7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9")
        # not built-in
        rinkeby_network = get_ethereum_network_info_with_definition(chain_id=4)
        kc_token = get_ethereum_token_info_with_definition(chain_id=4)

        # these variations should have the same result - successfully load built-in or encoded network/token
        calls_params = [
            (None, None, eth_network.info.chain_id, aave_token.info.address, eth_network.info, aave_token.info),
            (rinkeby_network.definition, None, eth_network.info.chain_id, aave_token.info.address, eth_network.info, aave_token.info),
            (None, kc_token.definition, eth_network.info.chain_id, aave_token.info.address, eth_network.info, aave_token.info),
            (rinkeby_network.definition, kc_token.definition, eth_network.info.chain_id, aave_token.info.address, eth_network.info, aave_token.info),
            (rinkeby_network.definition, kc_token.definition, None, kc_token.info.address, rinkeby_network.info, kc_token.info),
            (rinkeby_network.definition, kc_token.definition, rinkeby_network.info.chain_id, None, rinkeby_network.info, kc_token.info),
            (rinkeby_network.definition, kc_token.definition, None, None, rinkeby_network.info, kc_token.info),
        ]
        for params in calls_params:
            self.get_and_compare_ethereum_definitions(*params)

    def test_no_network_or_token(self):
        rinkeby_network = get_ethereum_network_info_with_definition(chain_id=4)
        kc_token = get_ethereum_token_info_with_definition(chain_id=4)

        calls_params = [
            # without network there should be no token loaded
            (None, kc_token.definition, None, kc_token.info.address, None, None),
            (None, kc_token.definition, 0, kc_token.info.address, None, None), # non-existing chain_id

            # also without token there should be no token loaded
            (rinkeby_network.definition, None, rinkeby_network.info.chain_id, None, rinkeby_network.info, None),
            (rinkeby_network.definition, None, rinkeby_network.info.chain_id, kc_token.info.address + b"\x00", rinkeby_network.info, None), # non-existing token address
        ]
        for params in calls_params:
            self.get_and_compare_ethereum_definitions(*params)


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestGetDefinitonsFromMsg(unittest.TestCase):
    def setUp(self):
        # use mockup functions for built-in definitions
        networks._networks_iterator = builtin_networks_iterator
        tokens.token_by_chain_address = builtin_token_by_chain_address

    def get_and_compare_ethereum_definitions(
        self,
        msg: protobuf.MessageType,
        network_info: EthereumNetworkInfo | None,
        token_info: EthereumTokenInfo | None,
    ):
        # get
        definitions = dfs.get_definitions_from_msg(msg)

        ref_token_dict = dict()
        if token_info is not None:
            ref_token_dict[token_info.address] = token_info

        # compare
        self.assertEqual(definitions.network, network_info)
        self.assertDictEqual(definitions.tokens, ref_token_dict)

    def test_get_definitions_SignTx_messages(self):
        # built-in
        eth_network = get_ethereum_network_info_with_definition(chain_id=1)
        aave_token = get_ethereum_token_info_with_definition(chain_id=1, token_address="7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9")
        # not built-in
        rinkeby_network = get_ethereum_network_info_with_definition(chain_id=4)
        kc_token = get_ethereum_token_info_with_definition(chain_id=4)

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
                    chain_id=rinkeby_network.info.chain_id,
                    to=hexlify(kc_token.info.address),
                    definitions=EthereumDefinitions(
                        encoded_network=rinkeby_network.definition,
                        encoded_token=kc_token.definition,
                    ),
                ),
                rinkeby_network.info,
                kc_token.info,
            ),
            (
                create_EthereumSignTx_msg(
                    chain_id=eth_network.info.chain_id,
                    to=hexlify(aave_token.info.address),
                ),
                eth_network.info,
                aave_token.info,
            ),
            (
                create_EthereumSignTxEIP1559_msg(
                    chain_id=rinkeby_network.info.chain_id,
                    to=hexlify(kc_token.info.address),
                    definitions=EthereumDefinitions(
                        encoded_network=rinkeby_network.definition,
                        encoded_token=kc_token.definition,
                    ),
                ),
                rinkeby_network.info,
                kc_token.info,
            ),
            (
                create_EthereumSignTxEIP1559_msg(
                    chain_id=eth_network.info.chain_id,
                    to=hexlify(aave_token.info.address),
                ),
                eth_network.info,
                aave_token.info,
            ),
        ]
        for params in params_set:
            self.get_and_compare_ethereum_definitions(*params)

        # missing "to" parameter in messages should lead to no token is loaded if none was provided
        params_set = [
            (
                create_EthereumSignTx_msg(
                    chain_id=rinkeby_network.info.chain_id,
                    definitions=EthereumDefinitions(
                        encoded_network=rinkeby_network.definition,
                        encoded_token=None,
                    ),
                ),
                rinkeby_network.info,
                None,
            ),
            (
                create_EthereumSignTx_msg(
                    chain_id=eth_network.info.chain_id,
                ),
                eth_network.info,
                None,
            ),
            (
                create_EthereumSignTxEIP1559_msg(
                    chain_id=rinkeby_network.info.chain_id,
                    definitions=EthereumDefinitions(
                        encoded_network=rinkeby_network.definition,
                        encoded_token=None
                    ),
                ),
                rinkeby_network.info,
                None,
            ),
            (
                create_EthereumSignTxEIP1559_msg(
                    chain_id=eth_network.info.chain_id,
                ),
                eth_network.info,
                None,
            ),
        ]
        for params in params_set:
            self.get_and_compare_ethereum_definitions(*params)

    def test_other_messages(self):
        rinkeby_network = get_ethereum_network_info_with_definition(chain_id=4)

        # only network should be loaded
        messages = [
            EthereumGetAddress(encoded_network=rinkeby_network.definition),
            EthereumGetPublicKey(encoded_network=rinkeby_network.definition),
            EthereumSignMessage(message=b'', encoded_network=rinkeby_network.definition),
            EthereumSignTypedData(primary_type="", encoded_network=rinkeby_network.definition),
            EthereumVerifyMessage(signature=b'', message=b'', address="", encoded_network=rinkeby_network.definition),
        ]
        for msg in messages:
            self.get_and_compare_ethereum_definitions(msg, rinkeby_network.info, None)

        # neither network nor token should be loaded
        messages = [
            EthereumGetAddress(),
            EthereumGetPublicKey(),
            EthereumSignMessage(message=b''),
            EthereumSignTypedData(primary_type=""),
            EthereumVerifyMessage(signature=b'', message=b'', address=""),
        ]
        for msg in messages:
            self.get_and_compare_ethereum_definitions(msg, None, None)

    def test_invalid_message(self):
        # msg without any of the required fields - chain_id, to, definitions, encoded_network
        class InvalidMsg():
            pass

        self.get_and_compare_ethereum_definitions(InvalidMsg(), None, None)


if __name__ == "__main__":
    unittest.main()
