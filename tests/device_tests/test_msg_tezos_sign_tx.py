# This file is part of the Trezor project.
#
# Copyright (C) 2012-2019 SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

import pytest

from trezorlib import messages, tezos
from trezorlib.protobuf import dict_to_proto
from trezorlib.tools import parse_path

TEZOS_PATH = parse_path("m/44'/1729'/0'")
TEZOS_PATH_10 = parse_path("m/44'/1729'/10'")
TEZOS_PATH_15 = parse_path("m/44'/1729'/15'")


@pytest.mark.altcoin
@pytest.mark.tezos
@pytest.mark.skip_t1
class TestMsgTezosSignTx:
    def test_tezos_sign_tx_proposal(self, client):
        with client:
            resp = tezos.sign_tx(
                client,
                TEZOS_PATH_10,
                dict_to_proto(
                    messages.TezosSignTx,
                    {
                        "branch": "dee04042c0832d68a43699b2001c0a38065436eb05e578071a763e1972d0bc81",
                        "proposal": {
                            "source": "005f450441f41ee11eee78a31d1e1e55627c783bd6",
                            "period": 17,
                            "proposals": [
                                "dfa974df171c2dad9a9b8f25d99af41fd9702ce5d04521d2f9943c84d88aa572"
                            ],
                        },
                    },
                ),
            )

        assert (
            resp.signature
            == "edsigtfY16R32k2WVMYfFr7ymnro4ib5zMckk28vsuViYNN77DJAvCJLRNArd9L531pUCxT4YdcvCvBym5dhcZ1rknEVm6yZ8bB"
        )
        assert (
            resp.sig_op_contents.hex()
            == "dee04042c0832d68a43699b2001c0a38065436eb05e578071a763e1972d0bc8105005f450441f41ee11eee78a31d1e1e55627c783bd60000001100000020dfa974df171c2dad9a9b8f25d99af41fd9702ce5d04521d2f9943c84d88aa5723b12621296a679b3a74ea790df5347995a76e20a09e76590baaacf4e09341965a04123f5cbbba8427f045b5f7d59157a3098e44839babe7c247d19b58bbb2405"
        )
        assert (
            resp.operation_hash == "opLqntFUu984M7LnGsFvfGW6kWe9QjAz4AfPDqQvwJ1wPM4Si4c"
        )

    def test_tezos_sign_tx_multiple_proposals(self, client):
        with client:
            resp = tezos.sign_tx(
                client,
                TEZOS_PATH_10,
                dict_to_proto(
                    messages.TezosSignTx,
                    {
                        "branch": "7e0be36a90c663c73c60da3889ffefff1383fb65cc29f0639f173d8f95a52df7",
                        "proposal": {
                            "source": "005f450441f41ee11eee78a31d1e1e55627c783bd6",
                            "period": 17,
                            "proposals": [
                                "2a6ff28ab4d0ccb18f7129aaaf9a4b8027d794f2562849665fdb6999db2a4e57",
                                "47cd60c09ab8437cc9fe19add494dce1b9844100f660f02ce77510a0c66d2762",
                            ],
                        },
                    },
                ),
            )

        assert (
            resp.signature
            == "edsigu6GAjhiWAQ64ctWTGEDYAZ16tYzLgzWzqc4CUyixK4FGRE8YUBVzFaVJ2fUCexZjZLMLdiNZGcUdzeL1bQhZ2h5oLrh7pA"
        )
        assert (
            resp.sig_op_contents.hex()
            == "7e0be36a90c663c73c60da3889ffefff1383fb65cc29f0639f173d8f95a52df705005f450441f41ee11eee78a31d1e1e55627c783bd600000011000000402a6ff28ab4d0ccb18f7129aaaf9a4b8027d794f2562849665fdb6999db2a4e5747cd60c09ab8437cc9fe19add494dce1b9844100f660f02ce77510a0c66d2762f813361ac00ada7e3256f23973ae25b112229476a3cb3e506fe929ea1e9358299fed22178d1be689cddeedd1f303abfef859b664f159a528576a1c807079f005"
        )
        assert (
            resp.operation_hash == "onobSyNgiitGXxSVFJN6949MhUomkkxvH4ZJ2owgWwNeDdntF9Y"
        )

    def test_tezos_sing_tx_ballot_yay(self, client):
        resp = tezos.sign_tx(
            client,
            TEZOS_PATH_10,
            dict_to_proto(
                messages.TezosSignTx,
                {
                    "branch": "3a8f60c4cd394cee5b50136c7fc8cb157e8aaa476a9e5c68709be6fc1cdb5395",
                    "ballot": {
                        "source": "0002298c03ed7d454a101eb7022bc95f7e5f41ac78",
                        "period": 2,
                        "proposal": "def7ed9c84af23ab37ebb60dd83cd103d1272ad6c63d4c05931567e65ed027e3",
                        "ballot": 0,
                    },
                },
            ),
        )

        assert (
            resp.signature
            == "edsigtkxNm6YXwtV24DqeuimeZFTeFCn2jDYheSsXT4rHMcEjNvzsiSo55nVyVsQxtEe8M7U4PWJWT4rGYYGckQCgtkNJkd2roX"
        )

    def test_tezos_sing_tx_ballot_nay(self, client):
        resp = tezos.sign_tx(
            client,
            TEZOS_PATH_10,
            dict_to_proto(
                messages.TezosSignTx,
                {
                    "branch": "3a8f60c4cd394cee5b50136c7fc8cb157e8aaa476a9e5c68709be6fc1cdb5395",
                    "ballot": {
                        "source": "0002298c03ed7d454a101eb7022bc95f7e5f41ac78",
                        "period": 2,
                        "proposal": "def7ed9c84af23ab37ebb60dd83cd103d1272ad6c63d4c05931567e65ed027e3",
                        "ballot": 1,
                    },
                },
            ),
        )
        assert (
            resp.signature
            == "edsigtqLaizfF6Cfc2JQL7TrsyniGhpZEojZAKMFW6AeudaUoU8KGXEHJH69Q4Lf27qFyUSTfbeHNnnCt69SGEPWkmpkgkgqMbL"
        )

    def test_tezos_sing_tx_ballot_pass(self, client):
        resp = tezos.sign_tx(
            client,
            TEZOS_PATH_10,
            dict_to_proto(
                messages.TezosSignTx,
                {
                    "branch": "3a8f60c4cd394cee5b50136c7fc8cb157e8aaa476a9e5c68709be6fc1cdb5395",
                    "ballot": {
                        "source": "0002298c03ed7d454a101eb7022bc95f7e5f41ac78",
                        "period": 2,
                        "proposal": "def7ed9c84af23ab37ebb60dd83cd103d1272ad6c63d4c05931567e65ed027e3",
                        "ballot": 2,
                    },
                },
            ),
        )

        assert (
            resp.signature
            == "edsigu6YX7EegPwrpcEbdNQsNhrRiEagBNGJBmFamP4mixZZw1UynhahGQ8RNiZLSUVLERUZwygrsSVenBqXGt9VnknTxtzjKzv"
        )

    def test_tezos_sign_tx_tranasaction(self, client):
        resp = tezos.sign_tx(
            client,
            TEZOS_PATH_10,
            dict_to_proto(
                messages.TezosSignTx,
                {
                    "branch": "3b85532b5a468cd26b6d3c7e762ae53b795d19c6db4838ed2750df8e063aedb8",
                    "transaction": {
                        "source": "005f450441f41ee11eee78a31d1e1e55627c783bd6",
                        "fee": 10000,
                        "counter": 274,
                        "gas_limit": 20000,
                        "storage_limit": 0,
                        "amount": 100000,
                        "destination": {
                            "tag": 0,
                            "hash": "003325df8851047421605ae7d6b09b49f70c8ce460",
                        },
                    },
                },
            ),
        )
        assert (
            resp.signature
            == "edsigtvRTDegGy83x5AHQwhzPAbKteJ7MsLukhLRS9RLMRX5UdmtV1xiHEhQCUrGNv6h9CbV1cvuUVzRgLd6Af4XfVQgGkkYUuY"
        )
        assert (
            resp.sig_op_contents.hex()
            == "3b85532b5a468cd26b6d3c7e762ae53b795d19c6db4838ed2750df8e063aedb86c005f450441f41ee11eee78a31d1e1e55627c783bd6904e9202a09c0100a08d0600003325df8851047421605ae7d6b09b49f70c8ce46000acdcd3df9daaa79c7345c068ffddc2113047fc00c1eed3503838d15fc6690821ee6eaa1e67b4a8d40dcf30a9ec456bbbda18ef2bcc021053d7d8c3f1473df809"
        )
        assert (
            resp.operation_hash == "oon8PNUsPETGKzfESv1Epv4535rviGS7RdCfAEKcPvzojrcuufb"
        )

    def test_tezos_sign_tx_delegation(self, client):
        resp = tezos.sign_tx(
            client,
            TEZOS_PATH_15,
            dict_to_proto(
                messages.TezosSignTx,
                {
                    "branch": "447d51450749763989c1aa5e1939aae623abb5a050f9cf1c04c247d91ca67593",
                    "delegation": {
                        "source": "0002eca091abc1e0f5c38a155c1313c410b47e1549",
                        "fee": 20000,
                        "counter": 458069,
                        "gas_limit": 20000,
                        "storage_limit": 0,
                        "delegate": "005f450441f41ee11eee78a31d1e1e55627c783bd6",
                    },
                },
            ),
        )
        assert (
            resp.signature
            == "edsigu2ZsDXXm7RzMF2oSKHK54ZfSUPvU2jekJBQmAprMe8ksnofMScKd3Kc3RTTExwzaJGENzoe94ZDiW86eWWnWBTPNw2xu5m"
        )
        assert (
            resp.sig_op_contents.hex()
            == "447d51450749763989c1aa5e1939aae623abb5a050f9cf1c04c247d91ca675936e0002eca091abc1e0f5c38a155c1313c410b47e1549a09c01d5fa1ba09c0100ff005f450441f41ee11eee78a31d1e1e55627c783bd6dbd53f9129387e82548e5d20b1479a46a876ac7516001fae01488dfbe9dcfc732cb8664d52fd7e1bc25a9845714131fd498ef65ea91f84e180688a41e06fe700"
        )
        assert (
            resp.operation_hash == "op79C1tR7wkUgYNid2zC1WNXmGorS38mTXZwtAjmCQm2kG7XG59"
        )

    def test_tezos_sign_tx_origination(self, client):
        resp = tezos.sign_tx(
            client,
            TEZOS_PATH_10,
            dict_to_proto(
                messages.TezosSignTx,
                {
                    "branch": "927ac7cd7969bde606e7537712584eb0d34fc52d9f5a88cc908994d817170a16",
                    "origination": {
                        "source": "005f450441f41ee11eee78a31d1e1e55627c783bd6",
                        "fee": 20000,
                        "counter": 276,
                        "gas_limit": 20000,
                        "storage_limit": 10000,
                        "balance": 100000,
                        "delegate": "00001e65c88ae6317cd62a638c8abd1e71c83c8475",
                        "script": "0000001c02000000170500036805010368050202000000080316053d036d03420000000a010000000568656c6c6f",
                    },
                },
            ),
        )
        assert (
            resp.signature
            == "edsigu5XoEibne4CCk3fHnwVzQwd3C9AYykWnmjX6PmezGN1ei7PospbKU21XJ3cCLUnxw8jacyET15GnaDX4buHwxtMaoX9FAM"
        )
        assert (
            resp.sig_op_contents.hex()
            == "927ac7cd7969bde606e7537712584eb0d34fc52d9f5a88cc908994d817170a166d005f450441f41ee11eee78a31d1e1e55627c783bd6a09c019402a09c01904ea08d06ff00001e65c88ae6317cd62a638c8abd1e71c83c84750000001c02000000170500036805010368050202000000080316053d036d03420000000a010000000568656c6c6ff27dbda99889ed106fedc692b0943da00aa7ff52fc6b1fb8dcde717119113539f0b1ecdb255ced04988c5537f3043362beb67b9fcac537ed8d18b4f3d1f97f0c"
        )
        assert (
            resp.operation_hash == "oo6uNxDaFCqaUzDqPfxjW7W1fg3AY7jWhH919DSrvGXnvquVcSZ"
        )

    def test_tezos_sign_tx_reveal(self, client):
        resp = tezos.sign_tx(
            client,
            TEZOS_PATH,
            dict_to_proto(
                messages.TezosSignTx,
                {
                    "branch": "f26502c204619c4bdab2e59efc50c79bc0136d781304b8f7fad389263550300e",
                    "reveal": {
                        "source": "00001e65c88ae6317cd62a638c8abd1e71c83c8475",
                        "fee": 20000,
                        "counter": 564560,
                        "gas_limit": 20000,
                        "storage_limit": 0,
                        "public_key": "00200da2c0200927dd8168b2b62e1322637521fcefb3184e61c1c3123c7c00bb95",
                    },
                    "transaction": {
                        "source": "00001e65c88ae6317cd62a638c8abd1e71c83c8475",
                        "fee": 50000,
                        "counter": 564561,
                        "gas_limit": 20000,
                        "storage_limit": 0,
                        "amount": 100000,
                        "destination": {
                            "tag": 0,
                            "hash": "005f450441f41ee11eee78a31d1e1e55627c783bd6",
                        },
                    },
                },
            ),
        )
        assert (
            resp.signature
            == "edsigtcqDr47paEVgr8X8gmvFt9UnNWACkMVCGdVFZ2yUq849oxmTbx2FqjToveUNwNujC9qmoi5kXWy78qZY2d5Qeryx6kCbGs"
        )
        assert (
            resp.sig_op_contents.hex()
            == "f26502c204619c4bdab2e59efc50c79bc0136d781304b8f7fad389263550300e6b00001e65c88ae6317cd62a638c8abd1e71c83c8475a09c01d0ba22a09c010000200da2c0200927dd8168b2b62e1322637521fcefb3184e61c1c3123c7c00bb956c00001e65c88ae6317cd62a638c8abd1e71c83c8475d08603d1ba22a09c0100a08d0600005f450441f41ee11eee78a31d1e1e55627c783bd60026690d65407d6cda03cde8e3c17a22ffd0351f78c18c500f3997cbe311e12e6cc4b5ff40b339c7fba8b4c7d62329ea45da662340113a6da98b7510b40042f204"
        )
        assert (
            resp.operation_hash == "oo9JFiWTnTSvUZfajMNwQe1VyFN2pqwiJzZPkpSAGfGD57Z6mZJ"
        )

    def test_tezos_smart_contract_delegation(self, client):
        resp = tezos.sign_tx(
            client,
            TEZOS_PATH_10,
            dict_to_proto(
                messages.TezosSignTx,
                {
                    "branch": "49eead995833934ee2571c6cd6439897ee71b72a9e4d22f127e0c3d4ca69ba15",
                    "transaction": {
                        "source": "005f450441f41ee11eee78a31d1e1e55627c783bd6",
                        "fee": 10000,
                        "counter": 278,
                        "gas_limit": 25822,
                        "storage_limit": 0,
                        "amount": 0,
                        "destination": {
                            "tag": 1,
                            "hash": "c116a6c74bf00a5839b593838215fe1fcf2db59c00",
                        },
                        "parameters_manager": {
                            "set_delegate": "005f450441f41ee11eee78a31d1e1e55627c783bd6"
                        },
                    },
                },
            ),
        )
        assert (
            resp.signature
            == "edsigtw8uSW99pT4GUd1mS14DbczxVfTCJrKBy6bMckBknwAxwAF53yBXnQAZwZ9WWMKyGmbta8RgPs262b7hGGNxFyTM8zdPBd"
        )
        assert (
            resp.sig_op_contents.hex()
            == "49eead995833934ee2571c6cd6439897ee71b72a9e4d22f127e0c3d4ca69ba156c005f450441f41ee11eee78a31d1e1e55627c783bd6904e9602dec901000001c116a6c74bf00a5839b593838215fe1fcf2db59c00ff020000002f020000002a0320053d036d0743035d0a00000015005f450441f41ee11eee78a31d1e1e55627c783bd60346034e031bb2534eb5478c31d5ffbc13b4692a7f2b73aad16e2d8e0f7068110955aa9480a6432775ba301f24bc20e4c12cffc9fd1f27b44204f830ea7f4dec23a18e25450d"
        )
        assert (
            resp.operation_hash == "oo75gfQGGPEPChXZzcPPAGtYqCpsg2BS5q9gmhrU3NQP7CEffpU"
        )

    def test_tezos_kt_remove_delegation(self, client):
        resp = tezos.sign_tx(
            client,
            TEZOS_PATH_10,
            dict_to_proto(
                messages.TezosSignTx,
                {
                    "branch": "77a1800dd37b54f61755bd97b2a6759627c53a5f8afb00bdcf8255b5d23eff44",
                    "transaction": {
                        "source": "005f450441f41ee11eee78a31d1e1e55627c783bd6",
                        "fee": 10000,
                        "counter": 279,
                        "gas_limit": 25822,
                        "storage_limit": 0,
                        "amount": 0,
                        "destination": {
                            "tag": 1,
                            "hash": "c116a6c74bf00a5839b593838215fe1fcf2db59c00",
                        },
                        "parameters_manager": {"cancel_delegate": True},
                    },
                },
            ),
        )
        assert (
            resp.signature
            == "edsigtqZZd8r2cww5GvTpaJANizYyAAB8n2sByKJWYwgEQQu6gjzSi7mQ7NAxbwsCaHGUS3F87oDJ1J5mz8SM8KYVidQj1NUz8E"
        )
        assert (
            resp.sig_op_contents.hex()
            == "77a1800dd37b54f61755bd97b2a6759627c53a5f8afb00bdcf8255b5d23eff446c005f450441f41ee11eee78a31d1e1e55627c783bd6904e9702dec901000001c116a6c74bf00a5839b593838215fe1fcf2db59c00ff0200000013020000000e0320053d036d053e035d034e031b87b6a5f01c0689f8f453f2b23582a2891792087197e01276648eec734850999e54e9edd687efb9297e24a96d126dc1e6636e772aeab80d5bc6b3f9b55aa3a701"
        )
        assert (
            resp.operation_hash == "ootMi1tXbfoVgFyzJa8iXyR4mnHd5TxLm9hmxVzMVRkbyVjKaHt"
        )

    def test_tezos_smart_contract_transfer(self, client):
        resp = tezos.sign_tx(
            client,
            TEZOS_PATH_10,
            dict_to_proto(
                messages.TezosSignTx,
                {
                    "branch": "442b86e27a7b79d893262b4daee229818f71073827570c74fa3aa1da7929d16d",
                    "transaction": {
                        "source": "005f450441f41ee11eee78a31d1e1e55627c783bd6",
                        "fee": 10000,
                        "counter": 280,
                        "gas_limit": 36000,
                        "storage_limit": 0,
                        "amount": 0,
                        "destination": {
                            "tag": 1,
                            "hash": "c116a6c74bf00a5839b593838215fe1fcf2db59c00",
                        },
                        "parameters_manager": {
                            "transfer": {
                                "amount": 20000,
                                "destination": {
                                    "tag": 0,
                                    "hash": "005f450441f41ee11eee78a31d1e1e55627c783bd6",
                                },
                            }
                        },
                    },
                },
            ),
        )
        assert (
            resp.signature
            == "edsigtaY4HzLQ2oVDqnUAzbkSjGMQVBNHnBLq5t4TmVnsdAG8W4FWzeEnWbJXRQSTUKme3sXijve9vmDyAtim7HXeu9XhFJDrMo"
        )
        assert (
            resp.sig_op_contents.hex()
            == "442b86e27a7b79d893262b4daee229818f71073827570c74fa3aa1da7929d16d6c005f450441f41ee11eee78a31d1e1e55627c783bd6904e9802a09902000001c116a6c74bf00a5839b593838215fe1fcf2db59c00ff020000003902000000340320053d036d0743035d0a00000015005f450441f41ee11eee78a31d1e1e55627c783bd6031e0743036a00a0b802034f034d031b14dc70ef8db46c4b8f53e387ff3d642644af458f757ab85f9291727dc18bb09d7ec5790136b8cc428b165aec9cf628eeefc90aad526dc75e2aab203e57b8920f"
        )
        assert (
            resp.operation_hash == "ooRGGtCmoQDgB36XvQqmM7govc3yb77YDUoa7p2QS7on27wGRns"
        )

    def test_tezos_smart_contract_transfer_to_contract(self, client):
        resp = tezos.sign_tx(
            client,
            TEZOS_PATH_10,
            dict_to_proto(
                messages.TezosSignTx,
                {
                    "branch": "8c696f9eb98cd641e33b680f424f7334b903d2b0108f0f896e73e921c44bf4c9",
                    "transaction": {
                        "source": "005f450441f41ee11eee78a31d1e1e55627c783bd6",
                        "fee": 4813,
                        "counter": 272,
                        "gas_limit": 44725,
                        "storage_limit": 0,
                        "amount": 0,
                        "destination": {
                            "tag": 1,
                            "hash": "c116a6c74bf00a5839b593838215fe1fcf2db59c00",
                        },
                        "parameters_manager": {
                            "transfer": {
                                "amount": 200,
                                "destination": {
                                    "tag": 1,
                                    "hash": "8b83360512c6045c1185f8000de41302e23a220c00",
                                },
                            }
                        },
                    },
                },
            ),
        )
        assert (
            resp.sig_op_contents.hex()
            == "8c696f9eb98cd641e33b680f424f7334b903d2b0108f0f896e73e921c44bf4c96c005f450441f41ee11eee78a31d1e1e55627c783bd6cd259002b5dd02000001c116a6c74bf00a5839b593838215fe1fcf2db59c00ff020000005502000000500320053d036d0743036e0a00000016018b83360512c6045c1185f8000de41302e23a220c000555036c0200000015072f02000000090200000004034f032702000000000743036a008803034f034d031b911b8e7f22acdacc78e6d40566636a7029773c9ebfa741bb94bb58fb9e705d3ad695ac24fd1a58943c3070e9c38b0660671adb478233ae31005cd9139c84a80b"
        )
        assert (
            resp.signature
            == "edsigtrnr4jXpPZK1yFVGtsapR4VHKp9Gnz1Uj7G4AdAXVn8ug16tgUx5u3TsyYJFp9MzENKuVqotaEwco3JhAhKpbjxbBQhEsT"
        )
        assert (
            resp.operation_hash == "opUE4xNkiUyYmJwUUgAab9xqHE66FXEc6VNZq4ZXDiBJcYwqNJX"
        )
