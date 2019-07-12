import struct

import pytest

from trezorlib import btc, messages as proto
from trezorlib.ckd_public import deserialize
from trezorlib.tools import parse_path

from .common import MNEMONIC_ALLALLALL, TrezorTest


@pytest.mark.altcoin
class TestMsgSigntxElements(TrezorTest):
    @pytest.mark.setup_client(mnemonic=MNEMONIC_ALLALLALL)
    def test_send_p2sh_explicit(self, client):
        inp1 = _explicit_lbtc(
            proto.TxInputType(
                address_n=parse_path("49'/1'/0'/0/0"),
                # XNW67ZQA9K3AuXPBWvJH4zN2y5QBDTwy2Z
                amount=10000000,
                prev_hash=bytes.fromhex(
                    "8fd1363b341478b4c04000e4f8b502ba1ab98db667c712c380763e6e9caacc95"
                ),
                prev_index=0,
                script_type=proto.InputScriptType.SPENDP2SHWITNESS,
            )
        )
        out1 = _explicit_lbtc(
            proto.TxOutputType(
                address="2dpWh6jbhAowNsQ5agtFzi7j6nKscj6UnEr",  # 44'/1'/0'/0/0
                amount=9990000,
                script_type=proto.OutputScriptType.PAYTOADDRESS,
            )
        )
        out2 = _explicit_lbtc(proto.TxOutputType(address="", amount=10000))  # fee
        with client:
            client.set_expected_responses(
                [
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=1),
                    ),
                    proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=1),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(request_type=proto.RequestType.TXFINISHED),
                ]
            )
            _, serialized_tx = btc.sign_tx(
                client,
                "Elements",
                [inp1],
                [out1, out2],
                details=proto.SignTx(version=2, lock_time=0x1234),
                prev_txes=None,
            )

        assert serialized_tx.hex() == "".join(
            """
02000000
01

01
95ccaa9c6e3e7680c312c767b68db91aba02b5f8e40040c0b47814343b36d18f
00000000
17 1600140099a7ecbd938ed1839f5f6bf6d50933c6db9d5c
ffffffff

02
01230f4f5d4b7c6fa845806ee4f67713459e1b69e8e60fcee2e4940c7a0d5de1b2
010000000000986f70
00
19 76a914a579388225827d9f2fe9014add644487808c695d88ac
01230f4f5d4b7c6fa845806ee4f67713459e1b69e8e60fcee2e4940c7a0d5de1b2
010000000000002710
00
00

34120000

00
00
02
  47 304402203349ef6cad85ea7f4d1c9693678f551703d8a916f6aa5ac14a0f3d53eca1e10502204277c40b204bdd4bdd36b634f62a266a4730eaee83f2eda81c6f30186421604201
  21 033add1f0e8e3c3136f7428dd4a4de1057380bd311f5b0856e2269170b4ffa65bf
00

00 00
00 00
""".strip().split()
        )

    @pytest.mark.setup_client(mnemonic=MNEMONIC_ALLALLALL)
    def test_send_segwit_explicit(self, client):
        inp1 = _explicit_lbtc(
            proto.TxInputType(
                address_n=parse_path("84'/1'/0'/0/0"),
                # ert1qkvwu9g3k2pdxewfqr7syz89r3gj557l3xp9k2v
                amount=9870000,
                prev_hash=bytes.fromhex(
                    "1f9409ca03484a8c76b712374d4a5f4a73d2d290850c8f5d839dd1ee407e9476"
                ),
                prev_index=0,
                script_type=proto.InputScriptType.SPENDWITNESS,
            )
        )
        out1 = _explicit_lbtc(
            proto.TxOutputType(
                address="2dpWh6jbhAowNsQ5agtFzi7j6nKscj6UnEr",  # 44'/1'/0'/0/0
                amount=9860000,
                script_type=proto.OutputScriptType.PAYTOADDRESS,
            )
        )
        out2 = _explicit_lbtc(proto.TxOutputType(address="", amount=10000))  # fee
        with client:
            client.set_expected_responses(
                [
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=1),
                    ),
                    proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=1),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(request_type=proto.RequestType.TXFINISHED),
                ]
            )
            _, serialized_tx = btc.sign_tx(
                client,
                "Elements",
                [inp1],
                [out1, out2],
                details=proto.SignTx(version=2, lock_time=0x1234),
                prev_txes=None,
            )
            assert serialized_tx.hex() == "".join(
                """
02000000
01

01
76947e40eed19d835d8f0c8590d2d2734a5f4a4d3712b7768c4a4803ca09941f
00000000
00
ffffffff

02
01230f4f5d4b7c6fa845806ee4f67713459e1b69e8e60fcee2e4940c7a0d5de1b2
0100000000009673a0
00
1976a914a579388225827d9f2fe9014add644487808c695d88ac
01230f4f5d4b7c6fa845806ee4f67713459e1b69e8e60fcee2e4940c7a0d5de1b2
010000000000002710
00
00

34120000

00
00
02
 47 304402202e36cdf1cac38894e71b3b8dca5f8099c36a3cabbb3903a60fcd4f36de3f725f02203f60fcd01d8938385c571458e58e63eff84631ea9d9f46ed955de654b1d42cb001
 21 03adc58245cf28406af0ef5cc24b8afba7f1be6c72f279b642d85c48798685f862
00

00 00
00 00
""".strip().split()
            )

    @pytest.mark.setup_client(mnemonic=MNEMONIC_ALLALLALL)
    def test_send_elements_multisig(self, client):
        coin_name = "Elements"
        nodes = [
            btc.get_public_node(client, parse_path("49'/1'/%d'" % index))
            for index in (1, 2, 3)
        ]
        multisig = proto.MultisigRedeemScriptType(
            nodes=[deserialize(n.xpub) for n in nodes],
            address_n=[1, 0],
            signatures=[b"", b"", b""],
            m=2,
        )

        inp1 = _explicit_lbtc(
            proto.TxInputType(
                address_n=parse_path("49'/1'/1'/1/0"),
                prev_hash=bytes.fromhex(
                    "cdeb3c2fa32b057324a352565309ce7306bc8934816b8ad9980493052688a9d3"
                ),
                prev_index=1,
                script_type=proto.InputScriptType.SPENDP2SHWITNESS,
                multisig=multisig,
                amount=23600000,
            )
        )

        out1 = _explicit_lbtc(
            proto.TxOutputType(
                address_n=parse_path("49'/1'/7'/1/0"),
                amount=23590000,
                script_type=proto.OutputScriptType.PAYTOADDRESS,
            )
        )
        out2 = _explicit_lbtc(
            proto.TxOutputType(address="", amount=(inp1.amount - out1.amount))  # fee
        )

        with client:
            for i in (1, 2, 3):
                addr = btc.get_address(
                    client,
                    coin_name=coin_name,
                    n=parse_path("49'/1'/{}'/1/0".format(i)),
                    script_type=proto.InputScriptType.SPENDP2SHWITNESS,
                    multisig=multisig,
                )
                assert addr == "XDwVf1X6qA2Ehqrxsc4LTaf3rr2bkE2tkh"

            client.set_expected_responses(
                [
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=1),
                    ),
                    proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=1),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(request_type=proto.RequestType.TXFINISHED),
                ]
            )
            signatures, _ = btc.sign_tx(
                client,
                coin_name,
                [inp1],
                [out1, out2],
                details=proto.SignTx(version=2, lock_time=7),
                prev_txes=None,
            )
            # store signature
            inp1.multisig.signatures[0] = signatures[0]
            # sign with third key
            inp1.address_n = parse_path("49'/1'/3'/1/0")
            client.set_expected_responses(
                [
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=1),
                    ),
                    proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=1),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(request_type=proto.RequestType.TXFINISHED),
                ]
            )
            _, serialized_tx = btc.sign_tx(
                client,
                coin_name,
                [inp1],
                [out1, out2],
                details=proto.SignTx(version=2, lock_time=7),
                prev_txes=None,
            )

        assert (
            serialized_tx.hex()
            == """
02000000
01
01
d3a9882605930498d98a6b813489bc0673ce09535652a32473052ba32f3cebcd
01000000
23220020cf28684ff8a6dda1a7a9704dde113ddfcf236558da5ce35ad3f8477474dbdaf7
ffffffff

02
01230f4f5d4b7c6fa845806ee4f67713459e1b69e8e60fcee2e4940c7a0d5de1b2
01000000000167f470
00
1976a91436cd5d96706462c435eb21069a913dc759dd72b088ac
01230f4f5d4b7c6fa845806ee4f67713459e1b69e8e60fcee2e4940c7a0d5de1b2
010000000000002710
00
00

07000000

00
00
04
  00
  47304402207e7e0292857ffdf9bcaec5bd9f415486918041b09cf84455a5474de1c5376e82022015678925ddeee054f5e7505eb762f066ee999bdf8b919b106f837feaec93a84e01
  473044022073cadd030f4eda9dadbc5ae90ba67f1e339de9cd0e1d0f1afd46f3be11e305e20220174b488806670ea7f0777c46165db30593684cd123350bb9d4db1b53576d1cbd01
  69522103d54ab3c8b81cb7f8f8088df4c62c105e8acaa2fb53b180f6bc6f922faecf3fdc21036aa47994f3f18f0976d6073ca79997003c3fa29c4f93907998fefc1151b4529b2102a092580f2828272517c402da9461425c5032860ab40180e041fbbb88ea2a520453ae
0000000000
""".replace(
                " ", ""
            ).replace(
                "\n", ""
            )
        )
        print(serialized_tx.hex())


def _explicit_lbtc(obj):
    value = bytes([0x01]) + struct.pack(">Q", obj.amount)  # explicit amount
    asset = bytes.fromhex(  # expicit L-BTC tag
        "01230f4f5d4b7c6fa845806ee4f67713459e1b69e8e60fcee2e4940c7a0d5de1b2"
    )
    nonce = b"\x00"  # empty on non-confidential value
    obj.confidential_value = proto.TxConfidentialValue(
        value=value, asset=asset, nonce=nonce
    )
    return obj


# $ e1-cli sendtoaddress XDwVf1X6qA2Ehqrxsc4LTaf3rr2bkE2tkh 0.236 "" ""
# cdeb3c2fa32b057324a352565309ce7306bc8934816b8ad9980493052688a9d3

# $ e1-cli getrawtransaction cdeb3c2fa32b057324a352565309ce7306bc8934816b8ad9980493052688a9d3 1
# {
#   "txid": "cdeb3c2fa32b057324a352565309ce7306bc8934816b8ad9980493052688a9d3",
#   "hash": "4594667f9eabc960113d339eaf1b783b019aa73ed60b162b42fd34d887602e07",
#   "wtxid": "4594667f9eabc960113d339eaf1b783b019aa73ed60b162b42fd34d887602e07",
#   "withash": "9ae5a1a0e3d8cef1c1a8c4392672af67d1ae5bdcb736e6a290dfd64dbb6ad14a",
#   "version": 2,
#   "size": 369,
#   "vsize": 282,
#   "weight": 1128,
#   "locktime": 106,
#   "vin": [
#     {
#       "txid": "28511dfc356422406d42398f10362aefacc59e12d6239192cd75f707daf86df3",
#       "vout": 1,
#       "scriptSig": {
#         "asm": "00140329ce46bcea46a9d3b765b45347f3ca9309c843",
#         "hex": "1600140329ce46bcea46a9d3b765b45347f3ca9309c843"
#       },
#       "is_pegin": false,
#       "sequence": 4294967293,
#       "txinwitness": [
#         "30440220181e8cdaaab1e837da3e27ae5599b8b174f65aa61b247cc105af3f2f624104df02205a053a364d2c164d740e89dba427ab02cbc9e86af828adebc9e9247c838f01e401",
#         "0381f3e1370b68fc50edb109faed46c44aee3542fa12e37621c14caa72772c515c"
#       ]
#     }
#   ],
#   "vout": [
#     {
#       "value": 20999999.15183080,
#       "asset": "b2e15d0d7a0c94e4e2ce0fe6e8691b9e451377f6e46e8045a86f7c4b5d4f0f23",
#       "commitmentnonce": "",
#       "commitmentnonce_fully_valid": false,
#       "n": 0,
#       "scriptPubKey": {
#         "asm": "OP_HASH160 146da92e8022aa0faee10287a805afdeaa435eee OP_EQUAL",
#         "hex": "a914146da92e8022aa0faee10287a805afdeaa435eee87",
#         "reqSigs": 1,
#         "type": "scripthash",
#         "addresses": [
#           "XDDFjMNRn8J5MSAizg6ojHt7v1xWV3ukcJ"
#         ]
#       }
#     },
#     {
#       "value": 0.23600000,
#       "asset": "b2e15d0d7a0c94e4e2ce0fe6e8691b9e451377f6e46e8045a86f7c4b5d4f0f23",
#       "commitmentnonce": "",
#       "commitmentnonce_fully_valid": false,
#       "n": 1,
#       "scriptPubKey": {
#         "asm": "OP_HASH160 1c6ac16064f481c6557a6d5af6b380e99af3e250 OP_EQUAL",
#         "hex": "a9141c6ac16064f481c6557a6d5af6b380e99af3e25087",
#         "reqSigs": 1,
#         "type": "scripthash",
#         "addresses": [
#           "XDwVf1X6qA2Ehqrxsc4LTaf3rr2bkE2tkh"
#         ]
#       }
#     },
#     {
#       "value": 0.00005640,
#       "asset": "b2e15d0d7a0c94e4e2ce0fe6e8691b9e451377f6e46e8045a86f7c4b5d4f0f23",
#       "commitmentnonce": "",
#       "commitmentnonce_fully_valid": false,
#       "n": 2,
#       "scriptPubKey": {
#         "asm": "",
#         "hex": "",
#         "type": "fee"
#       }
#     }
#   ],
#   "hex": "020000000101f36df8da07f775cd929123d6129ec5acef2a36108f39426d40226435fc1d512801000000171600140329ce46bcea46a9d3b765b45347f3ca9309c843fdffffff0301230f4f5d4b7c6fa845806ee4f67713459e1b69e8e60fcee2e4940c7a0d5de1b201000775f054f90be80017a914146da92e8022aa0faee10287a805afdeaa435eee8701230f4f5d4b7c6fa845806ee4f67713459e1b69e8e60fcee2e4940c7a0d5de1b2010000000001681b800017a9141c6ac16064f481c6557a6d5af6b380e99af3e2508701230f4f5d4b7c6fa845806ee4f67713459e1b69e8e60fcee2e4940c7a0d5de1b201000000000000160800006a0000000000024730440220181e8cdaaab1e837da3e27ae5599b8b174f65aa61b247cc105af3f2f624104df02205a053a364d2c164d740e89dba427ab02cbc9e86af828adebc9e9247c838f01e401210381f3e1370b68fc50edb109faed46c44aee3542fa12e37621c14caa72772c515c00000000000000"
# }

# $ e1-cli sendrawtransaction 020000000101d3a9882605930498d98a6b813489bc0673ce09535652a32473052ba32f3cebcd0100000023220020cf28684ff8a6dda1a7a9704dde113ddfcf236558da5ce35ad3f8477474dbdaf7ffffffff0201230f4f5d4b7c6fa845806ee4f67713459e1b69e8e60fcee2e4940c7a0d5de1b201000000000167f470001976a91436cd5d96706462c435eb21069a913dc759dd72b088ac01230f4f5d4b7c6fa845806ee4f67713459e1b69e8e60fcee2e4940c7a0d5de1b20100000000000027100000070000000000040047304402207e7e0292857ffdf9bcaec5bd9f415486918041b09cf84455a5474de1c5376e82022015678925ddeee054f5e7505eb762f066ee999bdf8b919b106f837feaec93a84e01473044022073cadd030f4eda9dadbc5ae90ba67f1e339de9cd0e1d0f1afd46f3be11e305e20220174b488806670ea7f0777c46165db30593684cd123350bb9d4db1b53576d1cbd0169522103d54ab3c8b81cb7f8f8088df4c62c105e8acaa2fb53b180f6bc6f922faecf3fdc21036aa47994f3f18f0976d6073ca79997003c3fa29c4f93907998fefc1151b4529b2102a092580f2828272517c402da9461425c5032860ab40180e041fbbb88ea2a520453ae0000000000
# aca24f3e96323dbdec552df90fd36dcc021ccfdd15b1159409f7d1835171b2d4

# {
#   "txid": "aca24f3e96323dbdec552df90fd36dcc021ccfdd15b1159409f7d1835171b2d4",
#   "hash": "3b8ebaa3d6e237f738baa0eee1e9366b48f552ac41c651f6dd23b4830632c164",
#   "wtxid": "3b8ebaa3d6e237f738baa0eee1e9366b48f552ac41c651f6dd23b4830632c164",
#   "withash": "5457a655554dbce80729aaafe51e903c2d98de21c639867136a55d59f301d091",
#   "version": 2,
#   "size": 459,
#   "vsize": 265,
#   "weight": 1059,
#   "locktime": 7,
#   "vin": [
#     {
#       "txid": "cdeb3c2fa32b057324a352565309ce7306bc8934816b8ad9980493052688a9d3",
#       "vout": 1,
#       "scriptSig": {
#         "asm": "0020cf28684ff8a6dda1a7a9704dde113ddfcf236558da5ce35ad3f8477474dbdaf7",
#         "hex": "220020cf28684ff8a6dda1a7a9704dde113ddfcf236558da5ce35ad3f8477474dbdaf7"
#       },
#       "is_pegin": false,
#       "sequence": 4294967295,
#       "txinwitness": [
#         "",
#         "304402207e7e0292857ffdf9bcaec5bd9f415486918041b09cf84455a5474de1c5376e82022015678925ddeee054f5e7505eb762f066ee999bdf8b919b106f837feaec93a84e01",
#         "3044022073cadd030f4eda9dadbc5ae90ba67f1e339de9cd0e1d0f1afd46f3be11e305e20220174b488806670ea7f0777c46165db30593684cd123350bb9d4db1b53576d1cbd01",
#         "522103d54ab3c8b81cb7f8f8088df4c62c105e8acaa2fb53b180f6bc6f922faecf3fdc21036aa47994f3f18f0976d6073ca79997003c3fa29c4f93907998fefc1151b4529b2102a092580f2828272517c402da9461425c5032860ab40180e041fbbb88ea2a520453ae"
#       ]
#     }
#   ],
#   "vout": [
#     {
#       "value": 0.23590000,
#       "asset": "b2e15d0d7a0c94e4e2ce0fe6e8691b9e451377f6e46e8045a86f7c4b5d4f0f23",
#       "commitmentnonce": "",
#       "commitmentnonce_fully_valid": false,
#       "n": 0,
#       "scriptPubKey": {
#         "asm": "OP_DUP OP_HASH160 36cd5d96706462c435eb21069a913dc759dd72b0 OP_EQUALVERIFY OP_CHECKSIG",
#         "hex": "76a91436cd5d96706462c435eb21069a913dc759dd72b088ac",
#         "reqSigs": 1,
#         "type": "pubkeyhash",
#         "addresses": [
#           "2deRWtvnVHYzezmnr5Q6E9gRsTXwRJjSLK4"
#         ]
#       }
#     },
#     {
#       "value": 0.00010000,
#       "asset": "b2e15d0d7a0c94e4e2ce0fe6e8691b9e451377f6e46e8045a86f7c4b5d4f0f23",
#       "commitmentnonce": "",
#       "commitmentnonce_fully_valid": false,
#       "n": 1,
#       "scriptPubKey": {
#         "asm": "",
#         "hex": "",
#         "type": "fee"
#       }
#     }
#   ],
#   "hex": "020000000101d3a9882605930498d98a6b813489bc0673ce09535652a32473052ba32f3cebcd0100000023220020cf28684ff8a6dda1a7a9704dde113ddfcf236558da5ce35ad3f8477474dbdaf7ffffffff0201230f4f5d4b7c6fa845806ee4f67713459e1b69e8e60fcee2e4940c7a0d5de1b201000000000167f470001976a91436cd5d96706462c435eb21069a913dc759dd72b088ac01230f4f5d4b7c6fa845806ee4f67713459e1b69e8e60fcee2e4940c7a0d5de1b20100000000000027100000070000000000040047304402207e7e0292857ffdf9bcaec5bd9f415486918041b09cf84455a5474de1c5376e82022015678925ddeee054f5e7505eb762f066ee999bdf8b919b106f837feaec93a84e01473044022073cadd030f4eda9dadbc5ae90ba67f1e339de9cd0e1d0f1afd46f3be11e305e20220174b488806670ea7f0777c46165db30593684cd123350bb9d4db1b53576d1cbd0169522103d54ab3c8b81cb7f8f8088df4c62c105e8acaa2fb53b180f6bc6f922faecf3fdc21036aa47994f3f18f0976d6073ca79997003c3fa29c4f93907998fefc1151b4529b2102a092580f2828272517c402da9461425c5032860ab40180e041fbbb88ea2a520453ae0000000000",
#   "blockhash": "3ff1c00c89271615ff111622eaa7935cae95a4e38ad5a58048f0aea7ef8f6c82",
#   "confirmations": 1,
#   "time": 1564342016,
#   "blocktime": 1564342016
# }
