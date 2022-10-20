from common import *
from trezor import wire
from ubinascii import hexlify  # noqa: F401

if not utils.BITCOIN_ONLY:
    import apps.ethereum.definitions as dfs

    from apps.ethereum import tokens
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
class TestDecodeDefinition(unittest.TestCase):
    def test_short_message(self):
        with self.assertRaises(wire.DataError):
            dfs.decode_definition(b'\x00', EthereumNetworkInfo)
        with self.assertRaises(wire.DataError):
            dfs.decode_definition(b'\x00', EthereumTokenInfo)

    # successful decode network
    def test_network_definition(self):
        rinkeby_network = get_ethereum_network_info_with_definition(chain_id=4)
        self.assertEqual(dfs.decode_definition(rinkeby_network.definition, EthereumNetworkInfo), rinkeby_network.info)

    # successful decode token
    def test_token_definition(self):
        # Karma Token
        kc_token = get_ethereum_token_info_with_definition(chain_id=4)
        self.assertEqual(dfs.decode_definition(kc_token.definition, EthereumTokenInfo), kc_token.info)

    def test_invalid_data(self):
        rinkeby_network = get_ethereum_network_info_with_definition(chain_id=4)

        invalid_dataset = []

        # mangle Merkle tree proof
        invalid_dataset.append(bytearray(rinkeby_network.definition))
        invalid_dataset[-1][-65] += 1

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
                dfs.decode_definition(bytes(data), EthereumNetworkInfo)

    def test_wrong_requested_type(self):
        rinkeby_network = get_ethereum_network_info_with_definition(chain_id=4)
        with self.assertRaises(wire.DataError):
            dfs.decode_definition(rinkeby_network.definition, EthereumTokenInfo)


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestGetNetworkDefiniton(unittest.TestCase):
    def test_get_network_definition(self):
        eth_network = get_ethereum_network_info_with_definition(chain_id=1)
        self.assertEqual(dfs._get_network_definiton(1, None), eth_network.info)

    def test_built_in_preference(self):
        eth_network = get_ethereum_network_info_with_definition(chain_id=1)
        ubiq_network = get_ethereum_network_info_with_definition(chain_id=8)
        self.assertEqual(dfs._get_network_definiton(1, ubiq_network.definition), eth_network.info)

    def test_no_built_in(self):
        ubiq_network = get_ethereum_network_info_with_definition(chain_id=8)

        # use provided (encoded) definition
        self.assertEqual(dfs._get_network_definiton(8, ubiq_network.definition), ubiq_network.info)
        # here the result should be the same as above
        self.assertEqual(dfs._get_network_definiton(None, ubiq_network.definition), ubiq_network.info)
        # nothing should be found
        self.assertIsNone(dfs._get_network_definiton(8, None))
        self.assertIsNone(dfs._get_network_definiton(None, None))

        # reference chain_id is used to check the encoded network chain_id - so in case they do not equal
        # error is raised
        with self.assertRaises(wire.DataError):
            dfs._get_network_definiton(ubiq_network.info.chain_id + 9999, ubiq_network.definition)

    def test_invalid_encoded_definition(self):
        rinkeby_network = get_ethereum_network_info_with_definition(chain_id=4)
        definition = bytearray(rinkeby_network.definition)
        # mangle signature - this should have the same effect as it has in "decode_definition" function
        definition[-1] += 1
        with self.assertRaises(wire.DataError):
            dfs._get_network_definiton(None, bytes(definition))


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestGetTokenDefiniton(unittest.TestCase):
    def test_get_token_definition(self):
        aave_token = get_ethereum_token_info_with_definition(chain_id=1, token_address="7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9")
        self.assertEqual(dfs._get_token_definiton(aave_token.info.chain_id, aave_token.info.address, None), aave_token.info)

    def test_built_in_preference(self):
        aave_token = get_ethereum_token_info_with_definition(chain_id=1, token_address="7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9")
        adchain_token = get_ethereum_token_info_with_definition(chain_id=1, token_address="d0d6d6c5fe4a677d343cc433536bb717bae167dd")
        self.assertEqual(dfs._get_token_definiton(aave_token.info.chain_id, aave_token.info.address, adchain_token.definition), aave_token.info)

    def test_no_built_in(self):
        kc_token = get_ethereum_token_info_with_definition(chain_id=4)

        # use provided (encoded) definition
        self.assertEqual(dfs._get_token_definiton(kc_token.info.chain_id, kc_token.info.address, kc_token.definition), kc_token.info)
        # here the results should be the same as above
        self.assertEqual(dfs._get_token_definiton(None, kc_token.info.address, kc_token.definition), kc_token.info)
        self.assertEqual(dfs._get_token_definiton(kc_token.info.chain_id, None, kc_token.definition), kc_token.info)
        self.assertEqual(dfs._get_token_definiton(None, None, kc_token.definition), kc_token.info)
        # nothing should be found
        self.assertEqual(dfs._get_token_definiton(kc_token.info.chain_id, kc_token.info.address, None), tokens.UNKNOWN_TOKEN)
        self.assertEqual(dfs._get_token_definiton(None, kc_token.info.address, None), tokens.UNKNOWN_TOKEN)
        self.assertEqual(dfs._get_token_definiton(kc_token.info.chain_id, None, None), tokens.UNKNOWN_TOKEN)

        # reference chain_id and/or token address is used to check the encoded token chain_id/address - so in case they do not equal
        # tokens.UNKNOWN_TOKEN is returned
        self.assertEqual(dfs._get_token_definiton(kc_token.info.chain_id + 1, kc_token.info.address + b"\x00", kc_token.definition), tokens.UNKNOWN_TOKEN)
        self.assertEqual(dfs._get_token_definiton(kc_token.info.chain_id, kc_token.info.address + b"\x00", kc_token.definition), tokens.UNKNOWN_TOKEN)
        self.assertEqual(dfs._get_token_definiton(kc_token.info.chain_id + 1, kc_token.info.address, kc_token.definition), tokens.UNKNOWN_TOKEN)
        self.assertEqual(dfs._get_token_definiton(None, kc_token.info.address + b"\x00", kc_token.definition), tokens.UNKNOWN_TOKEN)
        self.assertEqual(dfs._get_token_definiton(kc_token.info.chain_id + 1, None, kc_token.definition), tokens.UNKNOWN_TOKEN)

    def test_invalid_encoded_definition(self):
        kc_token = get_ethereum_token_info_with_definition(chain_id=4)
        definition = bytearray(kc_token.definition)
        # mangle signature - this should have the same effect as it has in "decode_definition" function
        definition[-1] += 1
        with self.assertRaises(wire.DataError):
            dfs._get_token_definiton(None, None, bytes(definition))


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestEthereumDefinitions(unittest.TestCase):
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
        self.assertDictEqual(definitions.get_token(ref_token_address), ref_token_dict)

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
            (rinkeby_network.definition, kc_token.definition, rinkeby_network.info.chain_id, None, rinkeby_network.info, None),
            (rinkeby_network.definition, kc_token.definition, None, None, rinkeby_network.info, None),
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
    def get_and_compare_ethereum_definitions(
        self,
        msg: protobuf.MessageType,
        network_info: EthereumNetworkInfo | None,
        token_info: EthereumTokenInfo | None,
    ):
        # get
        definitions = dfs.get_definitions_from_msg(msg)

        ref_token_dict = dict()
        ref_token_addr = b""
        if token_info is not None:
            ref_token_dict[token_info.address] = token_info
            ref_token_addr = token_info.address

        # compare
        self.assertEqual(definitions.network, network_info)
        self.assertDictEqual(definitions.get_token(ref_token_addr), ref_token_dict)

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
