from common import *
from trezor import wire
from ubinascii import hexlify  # noqa: F401

if not utils.BITCOIN_ONLY:
    import apps.ethereum.definitions as dfs

    from ethereum_common import *
    from trezor import protobuf
    from trezor.enums import EthereumDefinitionType
    from trezor.messages import (
        EthereumEncodedDefinitions,
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
        self.format_version = b'trzd1' + b'\x00' * 3
        self.definition_type = b'\x02'
        self.data_version = b'\x00\x00\x00\x03'
        self.clean_payload = b'\x04' # optional length
        self.payload = self.format_version + self.definition_type + self.data_version + self.clean_payload
        self.signature = b'\x00' * 63 + b'\x05'
        self.definition = self.payload + self.signature

    def test_short_message(self):
        with self.assertRaises(wire.DataError):
            dfs.EthereumDefinitionParser(b'\x00' * (len(self.definition) - 1))

    def test_ok_message(self):
        parser = dfs.EthereumDefinitionParser(self.definition)
        self.assertEqual(parser.format_version, self.format_version.rstrip(b'\0').decode("utf-8"))
        self.assertEqual(parser.definition_type, int.from_bytes(self.definition_type, 'big'))
        self.assertEqual(parser.data_version, int.from_bytes(self.data_version, 'big'))
        self.assertEqual(parser.clean_payload, self.clean_payload)
        self.assertEqual(parser.payload, self.payload)
        self.assertEqual(parser.signature, self.signature)


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestDecodeDefinition(unittest.TestCase):
    def setUp(self):
        self.addTypeEqualityFunc(networks.NetworkInfo, equalNetworkInfo)
        self.addTypeEqualityFunc(tokens.TokenInfo, equalTokenInfo)

    # successful decode network
    def test_network_definition(self):
        eth_network = get_ethereum_network_info_with_definition(chain_id=1)
        self.assertEqual(dfs.decode_definition(eth_network.definition, EthereumDefinitionType.NETWORK), eth_network.info)

    # successful decode token
    def test_token_definition(self):
        # AAVE
        eth_token = get_ethereum_token_info_with_definition(chain_id=1, token_address="7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9")
        self.assertEqual(dfs.decode_definition(eth_token.definition, EthereumDefinitionType.TOKEN), eth_token.info)

    def test_invalid_data(self):
        eth_network = get_ethereum_network_info_with_definition(chain_id=1)

        invalid_dataset = []

        # mangle signature
        invalid_dataset.append(bytearray(eth_network.definition))
        invalid_dataset[-1][-1] += 1

        # mangle payload
        invalid_dataset.append(bytearray(eth_network.definition))
        invalid_dataset[-1][-65] += 1

        # wrong format version
        invalid_dataset.append(bytearray(eth_network.definition))
        invalid_dataset[-1][:5] = b'trzd2' # change "trzd1" to "trzd2"

        # wrong definition type
        invalid_dataset.append(bytearray(eth_network.definition))
        invalid_dataset[-1][8] += 1

        # wrong data format version
        invalid_dataset.append(bytearray(eth_network.definition))
        invalid_dataset[-1][13] += 1

        for data in invalid_dataset:
            with self.assertRaises(wire.DataError):
                dfs.decode_definition(bytes(data), EthereumDefinitionType.NETWORK)

    def test_wrong_requested_type(self):
        eth_network = get_ethereum_network_info_with_definition(chain_id=1)
        with self.assertRaises(wire.DataError):
            dfs.decode_definition(eth_network.definition, EthereumDefinitionType.TOKEN)


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestGetNetworkDefiniton(unittest.TestCase):
    def setUp(self):
        self.addTypeEqualityFunc(networks.NetworkInfo, equalNetworkInfo)

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
            dfs._get_network_definiton(ubiq_network.definition, ubiq_network.info.chain_id + 1)

    def test_invalid_encoded_definition(self):
        eth_network = get_ethereum_network_info_with_definition(chain_id=1)
        definition = bytearray(eth_network.definition)
        # mangle signature - this should have the same effect as it has in "decode_definition" function
        definition[-1] += 1
        with self.assertRaises(wire.DataError):
            dfs._get_network_definiton(bytes(definition), None)


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestGetTokenDefiniton(unittest.TestCase):
    def setUp(self):
        self.addTypeEqualityFunc(tokens.TokenInfo, equalTokenInfo)

    def test_get_token_definition(self):
        eth_token = get_ethereum_token_info_with_definition(chain_id=1)
        self.assertEqual(dfs._get_token_definiton(None, eth_token.info.chain_id, eth_token.info.address), eth_token.info)

    def test_built_in_preference(self):
        eth_token = get_ethereum_token_info_with_definition(chain_id=1)
        eth_classic_token = get_ethereum_token_info_with_definition(chain_id=61)
        self.assertEqual(dfs._get_token_definiton(eth_classic_token.definition, eth_token.info.chain_id, eth_token.info.address), eth_token.info)

    def test_no_built_in(self):
        eth_classic_token = get_ethereum_token_info_with_definition(chain_id=61)

        # use provided (encoded) definition
        self.assertEqual(dfs._get_token_definiton(eth_classic_token.definition, eth_classic_token.info.chain_id, eth_classic_token.info.address), eth_classic_token.info)
        # here the results should be the same as above
        self.assertEqual(dfs._get_token_definiton(eth_classic_token.definition, None, eth_classic_token.info.address), eth_classic_token.info)
        self.assertEqual(dfs._get_token_definiton(eth_classic_token.definition, eth_classic_token.info.chain_id, None), eth_classic_token.info)
        self.assertEqual(dfs._get_token_definiton(eth_classic_token.definition, None, None), eth_classic_token.info)
        # nothing should be found
        self.assertEqual(dfs._get_token_definiton(None, eth_classic_token.info.chain_id, eth_classic_token.info.address), tokens.UNKNOWN_TOKEN)
        self.assertEqual(dfs._get_token_definiton(None, None, eth_classic_token.info.address), tokens.UNKNOWN_TOKEN)
        self.assertEqual(dfs._get_token_definiton(None, eth_classic_token.info.chain_id, None), tokens.UNKNOWN_TOKEN)

        # reference chain_id and/or token address is used to check the encoded token chain_id/address - so in case they do not equal
        # tokens.UNKNOWN_TOKEN is returned
        self.assertEqual(dfs._get_token_definiton(eth_classic_token.definition, eth_classic_token.info.chain_id + 1, eth_classic_token.info.address + b"\x00"), tokens.UNKNOWN_TOKEN)
        self.assertEqual(dfs._get_token_definiton(eth_classic_token.definition, eth_classic_token.info.chain_id, eth_classic_token.info.address + b"\x00"), tokens.UNKNOWN_TOKEN)
        self.assertEqual(dfs._get_token_definiton(eth_classic_token.definition, eth_classic_token.info.chain_id + 1, eth_classic_token.info.address), tokens.UNKNOWN_TOKEN)
        self.assertEqual(dfs._get_token_definiton(eth_classic_token.definition, None, eth_classic_token.info.address + b"\x00"), tokens.UNKNOWN_TOKEN)
        self.assertEqual(dfs._get_token_definiton(eth_classic_token.definition, eth_classic_token.info.chain_id + 1, None), tokens.UNKNOWN_TOKEN)

    def test_invalid_encoded_definition(self):
        eth_token = get_ethereum_token_info_with_definition(chain_id=1)
        definition = bytearray(eth_token.definition)
        # mangle signature - this should have the same effect as it has in "decode_definition" function
        definition[-1] += 1
        with self.assertRaises(wire.DataError):
            dfs._get_token_definiton(bytes(definition), None, None)


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestEthereumDefinitons(unittest.TestCase):
    def setUp(self):
        self.addTypeEqualityFunc(networks.NetworkInfo, equalNetworkInfo)
        self.addTypeEqualityFunc(tokens.TokenInfo, equalTokenInfo)

    def get_and_compare_ethereum_definitions(
        self,
        network_definition: bytes | None,
        token_definition: bytes | None,
        ref_chain_id: int | None,
        ref_token_address: bytes | None,
        network_info: networks.NetworkInfo | None,
        token_info: tokens.TokenInfo | None,
    ):
        # get
        definitions = dfs.EthereumDefinitions(network_definition, token_definition, ref_chain_id, ref_token_address)

        ref_token_dict = dict()
        if token_info is not None:
            ref_token_dict[token_info.address] = token_info

        # compare
        self.assertEqual(definitions.network, network_info)
        self.assertDictEqual(definitions.token_dict, ref_token_dict)

    def test_get_definitions(self):
        eth_network = get_ethereum_network_info_with_definition(chain_id=1)
        eth_token = get_ethereum_token_info_with_definition(chain_id=1)

        # these variations should have the same result - successfully load built-in or encoded network/token
        calls_params = [
            (None, None, eth_network.info.chain_id, eth_token.info.address),
            (eth_network.definition, None, eth_network.info.chain_id, eth_token.info.address),
            (None, eth_token.definition, eth_network.info.chain_id, eth_token.info.address),
            (eth_network.definition, eth_token.definition, eth_network.info.chain_id, eth_token.info.address),
            (eth_network.definition, eth_token.definition, None, eth_token.info.address),
            (eth_network.definition, eth_token.definition, eth_network.info.chain_id, None),
            (eth_network.definition, eth_token.definition, None, None),
        ]
        for params in calls_params:
            self.get_and_compare_ethereum_definitions(*(params + (eth_network.info, eth_token.info)))

    def test_no_network_or_token(self):
        eth_network = get_ethereum_network_info_with_definition(chain_id=1)
        eth_token = get_ethereum_token_info_with_definition(chain_id=1)

        calls_params = [
            # without network there should be no token loaded
            (None, eth_token.definition, None, eth_token.info.address, None, None),
            (None, eth_token.definition, 0, eth_token.info.address, None, None), # non-existing chain_id

            # also without token there should be no token loaded
            (eth_network.definition, None, eth_network.info.chain_id, None, eth_network.info, None),
            (eth_network.definition, None, eth_network.info.chain_id, eth_token.info.address + b"\x00", eth_network.info, None), # non-existing token address
        ]
        for params in calls_params:
            self.get_and_compare_ethereum_definitions(*params)


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestGetDefinitonsFromMsg(unittest.TestCase):
    def setUp(self):
        self.addTypeEqualityFunc(networks.NetworkInfo, equalNetworkInfo)
        self.addTypeEqualityFunc(tokens.TokenInfo, equalTokenInfo)

    def get_and_compare_ethereum_definitions(
        self,
        msg: protobuf.MessageType,
        network_info: networks.NetworkInfo | None,
        token_info: tokens.TokenInfo | None,
    ):
        # get
        definitions = dfs.get_definitions_from_msg(msg)

        ref_token_dict = dict()
        if token_info is not None:
            ref_token_dict[token_info.address] = token_info

        # compare
        self.assertEqual(definitions.network, network_info)
        self.assertDictEqual(definitions.token_dict, ref_token_dict)

    def test_get_definitions_SignTx_messages(self):
        eth_network = get_ethereum_network_info_with_definition(chain_id=1)
        eth_token = get_ethereum_token_info_with_definition(chain_id=1)

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
        messages = [
            create_EthereumSignTx_msg(
                chain_id=eth_network.info.chain_id,
                to=hexlify(eth_token.info.address),
                definitions=EthereumEncodedDefinitions(eth_network.definition, eth_token.definition),
            ),
            create_EthereumSignTx_msg(
                chain_id=eth_network.info.chain_id,
                to=hexlify(eth_token.info.address),
            ),
            create_EthereumSignTxEIP1559_msg(
                chain_id=eth_network.info.chain_id,
                to=hexlify(eth_token.info.address),
                definitions=EthereumEncodedDefinitions(eth_network.definition, eth_token.definition),
            ),
            create_EthereumSignTxEIP1559_msg(
                chain_id=eth_network.info.chain_id,
                to=hexlify(eth_token.info.address),
            ),
        ]
        for msg in messages:
            self.get_and_compare_ethereum_definitions(msg, eth_network.info, eth_token.info)

        # missing "to" parameter in messages should lead to no token is loaded if none was provided
        messages = [
            create_EthereumSignTx_msg(
                chain_id=eth_network.info.chain_id,
                definitions=EthereumEncodedDefinitions(eth_network.definition, None),
            ),
            create_EthereumSignTx_msg(
                chain_id=eth_network.info.chain_id,
            ),
            create_EthereumSignTxEIP1559_msg(
                chain_id=eth_network.info.chain_id,
                definitions=EthereumEncodedDefinitions(eth_network.definition, None),
            ),
            create_EthereumSignTxEIP1559_msg(
                chain_id=eth_network.info.chain_id,
            ),
        ]
        for msg in messages:
            self.get_and_compare_ethereum_definitions(msg, eth_network.info, None)

    def test_other_messages(self):
        eth_network = get_ethereum_network_info_with_definition(chain_id=1)

        # only network should be loaded
        messages = [
            EthereumGetAddress(encoded_network=eth_network.definition),
            EthereumGetPublicKey(encoded_network=eth_network.definition),
            EthereumSignMessage(message=b'', encoded_network=eth_network.definition),
            EthereumSignTypedData(primary_type="", encoded_network=eth_network.definition),
            EthereumVerifyMessage(signature=b'', message=b'', address="", encoded_network=eth_network.definition),
        ]
        for msg in messages:
            self.get_and_compare_ethereum_definitions(msg, eth_network.info, None)

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
