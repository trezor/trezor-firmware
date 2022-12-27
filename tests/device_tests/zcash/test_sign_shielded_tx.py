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

from trezorlib import messages, zcash
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.exceptions import TrezorFailure
from trezorlib.messages import (
    ButtonRequest,
    OutputScriptType,
    RequestType as T,
    TxInputType,
    TxOutputType,
    TxRequest,
    TxRequestDetailsType,
    ZcashOrchardInput,
    ZcashOrchardOutput,
    ZcashSignatureType,
    Failure,
    FailureType,
)
from trezorlib.tools import parse_path

from ..bitcoin.signtx import request_finished, request_input, request_output

B = messages.ButtonRequestType


def request_orchard_input(i: int):
    return TxRequest(
        request_type=T.TXORCHARDINPUT,
        details=messages.TxRequestDetailsType(request_index=i),
    )


def request_orchard_output(i: int):
    return TxRequest(
        request_type=T.TXORCHARDOUTPUT,
        details=messages.TxRequestDetailsType(request_index=i),
    )


def request_no_op():
    return TxRequest(request_type=T.NO_OP)


def test_t2z(client: Client) -> None:
    inp_0 = TxInputType(
        address_n=parse_path("m/44h/1h/0h/0/0"),
        amount=1000000,
        prev_hash=bytes.fromhex("de0566f96c08e1d6efe753fe5940e48f7334f3d2af664818df358ff01c626f31"),
        prev_index=0,
    )
    out_0 = ZcashOrchardOutput(
        address=None,
        amount=990000,
        memo=None,
    )
    anchor = bytes.fromhex("91513dfdbb4453c947bca9d704c3284ce40378e8732b250e9ff2386efb7e493c")
    expected_shielding_seed = bytes.fromhex("663cac8eba02d5493e0c025e59147024290eaea1bf3b13fd73028576d8becfb2")
    expected_sighash = bytes.fromhex("317b60bdf6fa25e33c028c52cfa87a564f07375da69486d7946410b19c97847b")
    expected_serialized_tx = bytes.fromhex("050000800a27a726b4d0d6c2000000000000000001316f621cf08f35df184866afd2f334738fe44059fe53e7efd6e1086cf96605de000000006b483045022100c14c55fd9ec6f878318a9c190051bae369ee47146f73b401a95a3f1a9ce4419f02202156b592c8f25f454e780a79d5f1473e7c3a9254883690b0101ab0685a6d7c810121030e669acac1f280d1ddf441cd2ba5e97417bf2689e4bbec86df4f831bf9f7ffd0ffffffff00000002")

    with client:
        client.set_expected_responses(
            [
                request_input(0),
                request_orchard_output(0),
                ButtonRequest(code=B.SignTx),
                request_no_op(),  # shielding seed
                request_orchard_output(0),
                request_input(0),
                request_finished(),  # t-signature 0
            ]
        )

        protocol = zcash.sign_tx(
            client,
            inputs=[inp_0],
            outputs=[out_0],
            coin_name="Zcash Testnet",
            z_address_n=parse_path("m/32h/1h/0h"),
            anchor=anchor,
        )
        
        shielding_seed = next(protocol)
        assert shielding_seed == expected_shielding_seed
        sighash = next(protocol)
        assert sighash == expected_sighash
        signatures, serialized_tx = next(protocol)
        assert serialized_tx == expected_serialized_tx
        assert signatures == {
            ZcashSignatureType.TRANSPARENT: [
                bytes.fromhex("3045022100c14c55fd9ec6f878318a9c190051bae369ee47146f73b401a95a3f1a9ce4419f02202156b592c8f25f454e780a79d5f1473e7c3a9254883690b0101ab0685a6d7c81"),
            ],
            ZcashSignatureType.ORCHARD_SPEND_AUTH: {},
        }

        # Accepted by network as ccc0f99a8c9761aca546abbb8284686921b5511c53c68099c73353828319a14f


def test_long_memo(client: Client) -> None:
    # note e9410c3c645f1cf729207af23f2fc7e49e9397a714beb0a2c4fe32e759e95b07
    inp_0 = ZcashOrchardInput(
        recipient=bytes.fromhex("44a1a2b0e129b57e02d7cca0c0d666bac7de69f113c26e579c628545d58bf798e667b21ad7bcdd81e13914"),
        value=1000000,
        rho=bytes.fromhex("d46832bcfa437ba67525eccc55cc08a39c89498665554b80b88cc80a882f1f1e"),
        rseed=bytes.fromhex("c3de2d16a05cb9e8522f50f5c3bb189d8e28f04f78561d2fe1e7c9e16a6ce048"),
    )
    
    out_0 = ZcashOrchardOutput(
        address="utest1xt8k2akcdnncjfz8sfxkm49quc4w627skp3qpggkwp8c8ay3htftjf7tur9kftcw0w4vu4scwfg93ckfag84khy9k40yanl5k0qkanh9cyhddgws786qeqn37rtyf6rx4eflz09zk06",
        amount=990000,
        memo="Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Enim tortor at auctor urna nunc. Urna porttitor rhoncus dolor purus non enim praesent elementum facilisis. Amet purus gravida quis blandit turpis cursus in hac. Eu non diam phasellus vestibulum lorem sed risus. Pellentesque elit ullamcorper dignissim cras tincidunt. Egestas purus viverra accumsan in nisl nisi scelerisque eu ultrices. Morbi tincidunt ornare massa eget egestas purus.",
    )
    anchor = bytes.fromhex("91513dfdbb4453c947bca9d704c3284ce40378e8732b250e9ff2386efb7e493c")
    expected_shielding_seed = bytes.fromhex("1ab3209792a5f2c578d542c4e173dc5d41a2574a944c4fc1cbef3160eb3c91c5")
    expected_sighash = bytes.fromhex("5be775dd3eb9f994312a6c150bb7fa40d1a453b35442a4722573a2806c97ae53")
    expected_serialized_tx = bytes.fromhex("050000800a27a726b4d0d6c200000000000000000000000002")

    with client:
        client.set_expected_responses(
            [
                request_orchard_input(0),
                request_orchard_output(0),
                ButtonRequest(code=B.ConfirmOutput),
                ButtonRequest(code=B.SignTx),
                request_no_op(),  # shielding seed
                request_orchard_output(0),
                request_orchard_input(0),
                request_finished(),  # returns o-signature of o-input 0 in action 1
            ]
        )

        protocol = zcash.sign_tx(
            client,
            inputs=[inp_0],
            outputs=[out_0],
            coin_name="Zcash Testnet",
            z_address_n=parse_path("m/32h/1h/0h"),
            anchor=anchor,
        )
        
        shielding_seed = next(protocol)
        assert shielding_seed == expected_shielding_seed
        sighash = next(protocol)
        assert sighash == expected_sighash
        signatures, serialized_tx = next(protocol)
        assert serialized_tx == expected_serialized_tx
        assert signatures == {
            ZcashSignatureType.TRANSPARENT: [],
            ZcashSignatureType.ORCHARD_SPEND_AUTH: {
                1: bytes.fromhex("17c320df8c72b1f4cacdb075a4e52cf52a7ee41ff0568019269981c4dc3a3d84828321e25c60d1ac3d014f559c623e46e8bbd839f165d9f236aac09f0b51101a"),
            },
        }

        # Accepted by network as 53ae976c80a2732572a44254b353a4d140fab70b156c2a3194f9b93edd75e75b


def test_too_large_fee(client: Client) -> None:
    # note 3e44e6ed97e6a54299030fcc40be7f8b8135aad1e78c9de6af08b29a0fc79125
    inp_0 = ZcashOrchardInput(
        recipient=bytes.fromhex("e170dd1fa4e66e16058c912f073813435edf5204074c2f2972719ff48bdba64ca637b5519bd493dfcbb40c"),
        value=1000000,
        rho=bytes.fromhex("2d09ea3e03858fd48708abc9fde62d2519a671761400a1ae31f6151228c87d1a"),
        rseed=bytes.fromhex("e76bfafc8e2c660f7bf5af81c58f83648dd32b1bfc4d023390f59bad94899bb9"),
    )
    
    # note 17fd7fed11398c39ad54c5945764a1347249be752faf9426b50349125d55ba37
    inp_1 = ZcashOrchardInput(
        recipient=bytes.fromhex("3c16ab10809ca0c0164594ce7801e66a45b54993a153ce300594b17a83fe9528279856a906448ea41b6131"),
        value=1000000,
        rho=bytes.fromhex("8f3b7bac88aa1e7c1c320ad3ba56f5ff34f6cbbe716fe4a33a07a1d86181411b"),
        rseed=bytes.fromhex("cd51c1027ca0f2b3e6dda6ddfac93a807afd8e944b62fd2bb34fcbc330626527"),
    )
    
    out_0 = ZcashOrchardOutput(
        address="utest1xt8k2akcdnncjfz8sfxkm49quc4w627skp3qpggkwp8c8ay3htftjf7tur9kftcw0w4vu4scwfg93ckfag84khy9k40yanl5k0qkanh9cyhddgws786qeqn37rtyf6rx4eflz09zk06",
        amount=990000,
        memo="too large fee",
    )
    anchor = bytes.fromhex("880cb7d585cabeea07823afafd438008ab652f17b025147d001ca76c6f6ed420")

    with client:
        client.set_expected_responses(
            [
                request_orchard_input(0),
                request_orchard_input(1),
                request_orchard_output(0),
                ButtonRequest(code=B.ConfirmOutput),
                Failure,
            ]
        )

        with pytest.raises(TrezorFailure, match="DataError"):
            protocol = zcash.sign_tx(
                client,
                inputs=[inp_0, inp_1],
                outputs=[out_0],
                coin_name="Zcash Testnet",
                z_address_n=parse_path("m/32h/1h/0h"),
                anchor=anchor,
            )
            next(protocol)  # shielding seed
            next(protocol)  # sighash
            next(protocol)  # serialized_tx and signatures
        

def test_too_long_memo(client: Client) -> None:
    # note 521d740a5ac69a05871f5f267bf3d9d949dc190df55244d5c69f7f3a34ddf01f
    inp_0 = ZcashOrchardInput(
        recipient=bytes.fromhex("60fd17f3e0ada9aa1ec7f1b5d08c36e28fbf2bca109f78c4979ab2509c31bfced5d67e0bfda4143c870faa"),
        value=1000000,
        rho=bytes.fromhex("fb344f691582bc8126ed35ed7fd2eb67d826f85c2f6153c4596d7931c6a9ca08"),
        rseed=bytes.fromhex("c13b948c75fabcb9d2d89c98f41f836bcf307788910ee926ad468ff99215db23"),
    )
    
    out_0 = ZcashOrchardOutput(
        address="utest1xt8k2akcdnncjfz8sfxkm49quc4w627skp3qpggkwp8c8ay3htftjf7tur9kftcw0w4vu4scwfg93ckfag84khy9k40yanl5k0qkanh9cyhddgws786qeqn37rtyf6rx4eflz09zk06",
        amount=990000,
        memo="this memo hash 513 bytes this memo hash 513 bytes this memo hash 513 bytes this memo hash 513 bytes this memo hash 513 bytes this memo hash 513 bytes this memo hash 513 bytes this memo hash 513 bytes this memo hash 513 bytes this memo hash 513 bytes this memo hash 513 bytes this memo hash 513 bytes this memo hash 513 bytes this memo hash 513 bytes this memo hash 513 bytes this memo hash 513 bytes this memo hash 513 bytes this memo hash 513 bytes this memo hash 513 bytes this memo hash 513 bytes this memo has",
    )
    anchor = bytes.fromhex("880cb7d585cabeea07823afafd438008ab652f17b025147d001ca76c6f6ed420")

    with client:
        client.set_expected_responses(
            [
                request_orchard_input(0),
                request_orchard_output(0),
                Failure,
            ]
        )

        with pytest.raises(TrezorFailure, match="DataError"):
            protocol = zcash.sign_tx(
                client,
                inputs=[inp_0],
                outputs=[out_0],
                coin_name="Zcash Testnet",
                z_address_n=parse_path("m/32h/1h/0h"),
                anchor=anchor,
            )
            next(protocol)  # shielding seed
            next(protocol)  # sighash
            next(protocol)  # serialized_tx and signatures
        

def test_z2z(client: Client) -> None:
    # note 59edab53df258314c1439b13348de6f48d8a7e5f46433aeaa69cee09345ce81e
    inp_0 = ZcashOrchardInput(
        recipient=bytes.fromhex("44a1a2b0e129b57e02d7cca0c0d666bac7de69f113c26e579c628545d58bf798e667b21ad7bcdd81e13914"),
        value=1000000,
        rho=bytes.fromhex("fe73c10f9f39bbb651484512b574e7f82f46661aef6968c1de652aa0887b3339"),
        rseed=bytes.fromhex("8da24dc5800d366d6708871016189cb641367be404765b32be4e666fec6c7d5f"),
    )
    
    out_0 = ZcashOrchardOutput(
        address=None,
        amount=990000,
        memo=None,
    )
    anchor = bytes.fromhex("91513dfdbb4453c947bca9d704c3284ce40378e8732b250e9ff2386efb7e493c")
    expected_shielding_seed = bytes.fromhex("fb6715646149cf6e239908fd40ebb7c183aa87c62113848b63fb31411d4eb44e")
    expected_sighash = bytes.fromhex("6e678883fc87503ab9a7c8a7adc4c777920683f19cd1d29c5dbdd839acbc6d5d")
    expected_serialized_tx = bytes.fromhex("050000800a27a726b4d0d6c200000000000000000000000002")

    with client:
        client.set_expected_responses(
            [
                request_orchard_input(0),
                request_orchard_output(0),
                ButtonRequest(code=B.SignTx),
                request_no_op(),  # shielding seed
                request_orchard_output(0),
                request_orchard_input(0),
                request_finished(),  # returns o-signature of o-input 0 in action 1
            ]
        )

        protocol = zcash.sign_tx(
            client,
            inputs=[inp_0],
            outputs=[out_0],
            coin_name="Zcash Testnet",
            z_address_n=parse_path("m/32h/1h/0h"),
            anchor=anchor,
        )
        
        shielding_seed = next(protocol)
        assert shielding_seed == expected_shielding_seed
        sighash = next(protocol)
        assert sighash == expected_sighash
        signatures, serialized_tx = next(protocol)
        assert serialized_tx == expected_serialized_tx
        assert signatures == {
            ZcashSignatureType.TRANSPARENT: [],
            ZcashSignatureType.ORCHARD_SPEND_AUTH: {
                1: bytes.fromhex("01d2a88613ab48043e4ee8b36bbf3b4e2a7aded067893738761831a5c2275b83f5c9ee8515a77d3a9afa0c54c63b7f8c51df5318090bf583c3898ecdefaff80a"),
            },
        }

        # Accepted by network as 5d6dbcac39d8bd5d9cd2d19cf183069277c7c4ada7c8a7b93a5087fc8388676e


def test_dust_inputs(client: Client) -> None:
    # note d31b775654587b067aab9aeb80a6ca386ea3565ab40d7e8cfffe0ee00cd8ef2e
    inp_0 = ZcashOrchardInput(
        recipient=bytes.fromhex("44a1a2b0e129b57e02d7cca0c0d666bac7de69f113c26e579c628545d58bf798e667b21ad7bcdd81e13914"),
        value=1000000,
        rho=bytes.fromhex("8691c0292a9af2cee37e5e5d08ceac9712bd382ec918cee1a541c65b8c835b11"),
        rseed=bytes.fromhex("3136581d4003c4da40cc790f7d3f1918c6a09dc6a2fc6b77803bc4215501ec4f"),
    )
    
    # note 910e84948ed70ea5836790e95da310a66cd6bf8c7f60c187a92bce414c4dc704
    inp_1 = ZcashOrchardInput(
        recipient=bytes.fromhex("44a1a2b0e129b57e02d7cca0c0d666bac7de69f113c26e579c628545d58bf798e667b21ad7bcdd81e13914"),
        value=1000000,
        rho=bytes.fromhex("8f4571edfa70084c22c0b37d7adcc9da8f7b5945e4f943b25eca6b9c01d65f3c"),
        rseed=bytes.fromhex("9b9ec6d3f7339628a63f2f2dbf2c3540466ca4d242c8e882e64a139c6035a4e2"),
    )
    
    # note bcdfef4b79a8f424c1a8f02859c72eb2af5f1c14925ffbd1824c7c947ec16d1f
    inp_2 = ZcashOrchardInput(
        recipient=bytes.fromhex("44a1a2b0e129b57e02d7cca0c0d666bac7de69f113c26e579c628545d58bf798e667b21ad7bcdd81e13914"),
        value=1000000,
        rho=bytes.fromhex("29cb975a0fde20da2e4411d18e09080d5f95843c61409d63cdc2c107667fc222"),
        rseed=bytes.fromhex("e7fce58cafacd9e263d75b4bc7fba7666cc170a3c1b80d6a40c6588434c30dc5"),
    )
    
    # note f4b3dc901d26e355a6ede302257e56531ded7ca0cc88ae2ebb0c66195bff8c2f
    inp_3 = ZcashOrchardInput(
        recipient=bytes.fromhex("44a1a2b0e129b57e02d7cca0c0d666bac7de69f113c26e579c628545d58bf798e667b21ad7bcdd81e13914"),
        value=1000000,
        rho=bytes.fromhex("06ec68d839c3d174d065f51deea1740a7584fe2a3b5a6d4b09612fcbb99e3e2a"),
        rseed=bytes.fromhex("337f31ad99053ba832e9ea4553d479815ccfeea6d89b75fe845eb48b1f778564"),
    )
    
    # note 8d267d67f8f3cf2513cf0f5704ffdbfdebea13ec855d711e92e2fe0c2f493009
    inp_4 = ZcashOrchardInput(
        recipient=bytes.fromhex("44a1a2b0e129b57e02d7cca0c0d666bac7de69f113c26e579c628545d58bf798e667b21ad7bcdd81e13914"),
        value=1000000,
        rho=bytes.fromhex("7b559c4434eceb4f02e8588297a22c54b3e20899a4efba6e10c537191a8a0007"),
        rseed=bytes.fromhex("58e3bbc14e2a1b1cbdfeb655c37dc2a8d7fad20dcb738cde14e1a259586252c9"),
    )
    
    # note d1db87af77c8c3d30dd7c7a14c8b6cce47303199124c9bcbbf99fad790609225
    inp_5 = ZcashOrchardInput(
        recipient=bytes.fromhex("44a1a2b0e129b57e02d7cca0c0d666bac7de69f113c26e579c628545d58bf798e667b21ad7bcdd81e13914"),
        value=1000000,
        rho=bytes.fromhex("aa30929cc959b18ffdf5c9ccbb3147658724b544426d008b62c2a095db9a5923"),
        rseed=bytes.fromhex("a193a9812117e264152b15bff4ab67a4d77ff051733f5aacf05a1b0a6b8f4667"),
    )
    
    # note 4d82ae84eb35ca1f1dde94dbef4e1c81610a4b8fac3b93e9e2d0018204787826
    inp_6 = ZcashOrchardInput(
        recipient=bytes.fromhex("44a1a2b0e129b57e02d7cca0c0d666bac7de69f113c26e579c628545d58bf798e667b21ad7bcdd81e13914"),
        value=1000000,
        rho=bytes.fromhex("b05557518d6e3a75a46cf5660b00959e0da5411cfceecfa9b57d3337483c6830"),
        rseed=bytes.fromhex("37916b09f61734ef9157cdc5cf427592bdc1566fc6135e9b2ea21fc3a14b0d7b"),
    )
    
    # note 4b5728ee631d893d12800a4543f70b5b2cd5976d8f8849ae22ee7e158d93b502
    inp_7 = ZcashOrchardInput(
        recipient=bytes.fromhex("44a1a2b0e129b57e02d7cca0c0d666bac7de69f113c26e579c628545d58bf798e667b21ad7bcdd81e13914"),
        value=1000000,
        rho=bytes.fromhex("0c708f65e796eaaa94a3d94952be42a6bc721926dee260109dccde785156550e"),
        rseed=bytes.fromhex("bcf667423aaf2fd58c808039352fe6dcc0b3aa0360b5f80c255ffc78f628c1c9"),
    )
    
    # note a283d518363808f68bc237d7f94bcdfd4dcab85a2ce879e81aac40b342f5d512
    inp_8 = ZcashOrchardInput(
        recipient=bytes.fromhex("44a1a2b0e129b57e02d7cca0c0d666bac7de69f113c26e579c628545d58bf798e667b21ad7bcdd81e13914"),
        value=1000000,
        rho=bytes.fromhex("c3b688ea8c17bb403d00384881e612cd4a958d84e643c8b460497305c043912d"),
        rseed=bytes.fromhex("51c3ed91f9ba9860eead7e3b254b03d911c65259d2a930143d1e912d43a5b6f9"),
    )
    
    # note e06f775baf3f339f633dbfd0058d6e4298cf63f5c4acb3ddaf734b8d71dae03f
    inp_9 = ZcashOrchardInput(
        recipient=bytes.fromhex("44a1a2b0e129b57e02d7cca0c0d666bac7de69f113c26e579c628545d58bf798e667b21ad7bcdd81e13914"),
        value=1000000,
        rho=bytes.fromhex("7814a9ab7072b04a3f3b92478a4ffd4166aa453aaac15212b8b79faa98a0c905"),
        rseed=bytes.fromhex("d5351c4545b8c155bf9a6358201937e0cc188781180506f242542f1c712e5565"),
    )
    
    # note 59588bdb579fa64473bec97364ab4c24a3ded7f785d7179f2c5d72d44120ac39
    inp_10 = ZcashOrchardInput(
        recipient=bytes.fromhex("44a1a2b0e129b57e02d7cca0c0d666bac7de69f113c26e579c628545d58bf798e667b21ad7bcdd81e13914"),
        value=1000000,
        rho=bytes.fromhex("beeece26e589c9e394b89f1bcd962121c8b4799d13d54bf32b0823c7859fb33e"),
        rseed=bytes.fromhex("9ca1c83fed55891f64829ec821365498c2bf466bf0ea29ed3e4f882ea1deb201"),
    )
    
    # note 070060ac1eb6d8068c7f3c82cc946f6f1b978ce9470ec28d043348c80aeacb2d
    inp_11 = ZcashOrchardInput(
        recipient=bytes.fromhex("44a1a2b0e129b57e02d7cca0c0d666bac7de69f113c26e579c628545d58bf798e667b21ad7bcdd81e13914"),
        value=1000000,
        rho=bytes.fromhex("d45196d3f9c5b236874093f3a0ca953cb508c3877d4f6ce759d3ee0c3554502e"),
        rseed=bytes.fromhex("6ab596c96733e52bcaffbfdc52f41e7f00ebd22710878307ff4fcc16226810b9"),
    )
    
    out_0 = ZcashOrchardOutput(
        address="utest1rusrelt7xyc62chav9r6cv5nnxp63eemm3rm0qpaqs578hkjpr9rgyvuyjm3nxpcjfx8a7dquyt2shkw5xl23m523t3cgkt7wsd9mue3",
        amount=11990000,
        memo="dust inputs",
    )
    anchor = bytes.fromhex("91513dfdbb4453c947bca9d704c3284ce40378e8732b250e9ff2386efb7e493c")
    expected_shielding_seed = bytes.fromhex("17bdeea7f310d97df991a94a5292c3f19c92b1f77c2941927ddc15fbbbfbe7d9")
    expected_sighash = bytes.fromhex("1dfba8b01f871a258a8523cc79136b72c84d626e2dfca11b10ba96f065f4a1b9")
    expected_serialized_tx = bytes.fromhex("050000800a27a726b4d0d6c20000000000000000000000000c")

    with client:
        client.set_expected_responses(
            [
                ButtonRequest(code=B.Warning),
                request_orchard_input(0),
                request_orchard_input(1),
                request_orchard_input(2),
                request_orchard_input(3),
                request_orchard_input(4),
                request_orchard_input(5),
                request_orchard_input(6),
                request_orchard_input(7),
                request_orchard_input(8),
                request_orchard_input(9),
                request_orchard_input(10),
                request_orchard_input(11),
                request_orchard_output(0),
                ButtonRequest(code=B.ConfirmOutput),
                ButtonRequest(code=B.SignTx),
                request_no_op(),  # shielding seed
                request_orchard_input(6),
                request_orchard_input(5),
                request_orchard_input(8),
                request_orchard_input(4),
                request_orchard_input(1),
                request_orchard_input(11),
                request_orchard_input(2),
                request_orchard_input(0),
                request_orchard_input(10),
                request_orchard_input(3),
                request_orchard_output(0),
                request_orchard_input(9),
                request_orchard_input(7),
                request_no_op(),  # returns o-signature of o-input 6 in action 0
                request_no_op(),  # returns o-signature of o-input 5 in action 1
                request_no_op(),  # returns o-signature of o-input 8 in action 2
                request_no_op(),  # returns o-signature of o-input 4 in action 3
                request_no_op(),  # returns o-signature of o-input 1 in action 4
                request_no_op(),  # returns o-signature of o-input 11 in action 5
                request_no_op(),  # returns o-signature of o-input 2 in action 6
                request_no_op(),  # returns o-signature of o-input 0 in action 7
                request_no_op(),  # returns o-signature of o-input 10 in action 8
                request_no_op(),  # returns o-signature of o-input 3 in action 9
                request_no_op(),  # returns o-signature of o-input 9 in action 10
                request_finished(),  # returns o-signature of o-input 7 in action 11
            ]
        )

        protocol = zcash.sign_tx(
            client,
            inputs=[inp_0, inp_1, inp_2, inp_3, inp_4, inp_5, inp_6, inp_7, inp_8, inp_9, inp_10, inp_11],
            outputs=[out_0],
            coin_name="Zcash Testnet",
            z_address_n=parse_path("m/32h/1h/0h"),
            anchor=anchor,
        )
        
        shielding_seed = next(protocol)
        assert shielding_seed == expected_shielding_seed
        sighash = next(protocol)
        assert sighash == expected_sighash
        signatures, serialized_tx = next(protocol)
        assert serialized_tx == expected_serialized_tx
        assert signatures == {
            ZcashSignatureType.TRANSPARENT: [],
            ZcashSignatureType.ORCHARD_SPEND_AUTH: {
                0: bytes.fromhex("fde734e8c13a08abb29d58564b4ff4c70af2ea316fa78e98ac7c4a2e81f9e78a39a3648de21c7b592c3b365f565a5210f419e0344be672f2cbec61944c33f729"),
                1: bytes.fromhex("3827a44663562d4b8126ede68790d9f9e7dedeb30e09013f9757f10d76bb50ade01247f1ed8a1d23b54c3f1939a09beaa4efe900ff35756953c7e5b4c5e9fe39"),
                2: bytes.fromhex("6db8f7ac9c1bdb47fc44424c0bef85ebecfcbaf146387eafa74d921d9611382af1704579e62bfa95e2a1846f9441de99f73f04b6097823ddce71250519819b02"),
                3: bytes.fromhex("1caf83dd43b13f809e42f977a1aa6bf1c4a308eb3bb2764493f52515a15138ba2692bef2f11785e7f71dffc4181d771d4865f03e2cce2be2aa5c27b33cfb193b"),
                4: bytes.fromhex("ae123ecf50e53a1503cc9a6c863ed96d98c1b784144891d9849dd8e89ab2679b173204da524a9d1fd78aabe955bde82f5e97fe044a2c3c90f0554514d1275f29"),
                5: bytes.fromhex("ce0923be6364f2036cb5423d8294ea7608e9afa5fb12b8b832fbb0f4f7fe5f8d2c36aefad625666acdecfb12023058af780a22a1b016ef2504a2eafc3f6a8e1d"),
                6: bytes.fromhex("09ae97848cdc5869913ee731e243cf29ce0128079611c5fe59a25b00e76709a4331103ccc58c6273d93a7c6156534520cd14e5314c9dcc230c9e679b95e99434"),
                7: bytes.fromhex("b30176f365adf74b6dba9f019c2202ecd4ba230dc717106357b23d9cd765800d62ed6132c2f63ff8c5a7d3853c378d5c8fff6cde1c1531741ab87f8cac595518"),
                8: bytes.fromhex("575a95521b01ffe85f2e1b7963b0944feb6e4e6d6dbce12cc8c2159ac292bb11c3a851c03f315c2f92cc3e1e97eccef3e71ed7dd31d21f68d50149acb632ef35"),
                9: bytes.fromhex("efac7c0277ae71384fd8c6efd85109b8b82a8bd0fa13f70f91cb00ed3a639926a778d0ce9ae6e3e0e8ab453e4fe198ebd339ffaf49b41ff92f4d54c92bb6243e"),
                10: bytes.fromhex("49238482640c46f10227edc0e9e9bdd8e673b91af216211c8ebe00d77f6bad3c3316dc7aea32e0c0f9bbfb872ab65352adb9c143dd1c6184c502116a1e611216"),
                11: bytes.fromhex("f0d8ef38b95e5699f901b9333c37b92c9177401372b0712ae640f3fc0170e5881482bb98fe3bfe5ba0b238bae9826c86e3290e797443f26c3f693203810ed009"),
            },
        }

        # Accepted by network as b9a1f465f096ba101ba1fc2d6e624dc8726b1379cc23858a251a871fb0a8fb1d


def test_big_bundle(client: Client) -> None:
    # note 0976baf969f0b471f594922ad0e3bd72095cef0a59036bbe932116fd48af241d
    inp_0 = ZcashOrchardInput(
        recipient=bytes.fromhex("44a1a2b0e129b57e02d7cca0c0d666bac7de69f113c26e579c628545d58bf798e667b21ad7bcdd81e13914"),
        value=1000000,
        rho=bytes.fromhex("34c0297c0258d5adc98bd1ae74d50ddfe7b8d814b64ddb2b2bfd4c4e38763a36"),
        rseed=bytes.fromhex("cf53652d55c73b04a0d0863693c91c69e463b54f334e528e94fcc87944103dfb"),
    )
    
    # note 7419cdcd9db856735d0cab2e957ffc46328e9751f44f07d591950e2b60420b05
    inp_1 = ZcashOrchardInput(
        recipient=bytes.fromhex("44a1a2b0e129b57e02d7cca0c0d666bac7de69f113c26e579c628545d58bf798e667b21ad7bcdd81e13914"),
        value=1000000,
        rho=bytes.fromhex("1388dd2702f6ec29d8c3c902855728ee18a927ff7f04499fe66c7ef29d7a2c34"),
        rseed=bytes.fromhex("0b294ede38fc8e44c78311d201d5aa0d7922ff4e006ef9520fa8e6f823e5de29"),
    )
    
    # note 0cd344a3d2a45ef49b0c0f2699594689166d58537f1c6acd0838e02dac3d5123
    inp_2 = ZcashOrchardInput(
        recipient=bytes.fromhex("44a1a2b0e129b57e02d7cca0c0d666bac7de69f113c26e579c628545d58bf798e667b21ad7bcdd81e13914"),
        value=1000000,
        rho=bytes.fromhex("52cb572131824b6d460992e2d84faa954462de3fc3d9f45fee7eed451cd3f714"),
        rseed=bytes.fromhex("8f36b22a5ae001efdb382b3c15a4a3dd522e73190f88b00331152e84da3fc0db"),
    )
    
    # note 739e1bf4e4d0bcd111d2acbd6b0c0576942a03370055e14df15a1226ceca5d0e
    inp_3 = ZcashOrchardInput(
        recipient=bytes.fromhex("44a1a2b0e129b57e02d7cca0c0d666bac7de69f113c26e579c628545d58bf798e667b21ad7bcdd81e13914"),
        value=1000000,
        rho=bytes.fromhex("5b02bf645ea51b80c6f1b30ec19930733c164dd532bd74f14091db07a323140f"),
        rseed=bytes.fromhex("164a076614a1765e5b0c0af9301bac1a30ab93ccf20e092e406235cfb6374d83"),
    )
    
    # note 23f8ae325bbbd6d261250ca19db5ce2360d123600c05226721f61635df6db120
    inp_4 = ZcashOrchardInput(
        recipient=bytes.fromhex("44a1a2b0e129b57e02d7cca0c0d666bac7de69f113c26e579c628545d58bf798e667b21ad7bcdd81e13914"),
        value=1000000,
        rho=bytes.fromhex("95d53ff00b41cb366d1f47f58c3a9d2f986a06b98fad0c86014a19d513542a35"),
        rseed=bytes.fromhex("107dc126db8ce0fcbf82def750e400fa633064550db6bec21e79b4077a6911b0"),
    )
    
    # note 56c31200acb82de842e94e1d544a47aadf60c0d12f6f83b81b3bfeb9fad0be0c
    inp_5 = ZcashOrchardInput(
        recipient=bytes.fromhex("44a1a2b0e129b57e02d7cca0c0d666bac7de69f113c26e579c628545d58bf798e667b21ad7bcdd81e13914"),
        value=1000000,
        rho=bytes.fromhex("e273870f60877315f0206f9e2fdc2c49b0fb54a99a7dc82b8a9f674c0ac48b02"),
        rseed=bytes.fromhex("d8b7fb8bec1c205597752b9358acddeb37d8b2206e53d478dd991af02fa08fc8"),
    )
    
    # note 916529a6585e1105c08b1f1f522c8236c5815d13c6a47f6dd563f029cef58b10
    inp_6 = ZcashOrchardInput(
        recipient=bytes.fromhex("44a1a2b0e129b57e02d7cca0c0d666bac7de69f113c26e579c628545d58bf798e667b21ad7bcdd81e13914"),
        value=1000000,
        rho=bytes.fromhex("c14ef67ee7dde895ade762be84a649e91b850d3420c1b75cfa38ee19509ce434"),
        rseed=bytes.fromhex("b80a5c4cbba6871bb71ded3925ff50e43d127c78319fc8020d71d1a59ee4268a"),
    )
    
    # note 927296905d15708784e636f275a50835a4278f58e7282eaa17496e8d0becdd19
    inp_7 = ZcashOrchardInput(
        recipient=bytes.fromhex("44a1a2b0e129b57e02d7cca0c0d666bac7de69f113c26e579c628545d58bf798e667b21ad7bcdd81e13914"),
        value=1000000,
        rho=bytes.fromhex("e2ab3489decd228532ecf80d1b2d5add208d01d8be7d01d36da1e349b91f642c"),
        rseed=bytes.fromhex("11540047df0b296c28ca998fd4f5e33479b32d551e3bcfc6f417d43044a71763"),
    )
    
    out_0 = ZcashOrchardOutput(
        address="utest1gu6rg6hse8v0pd7mhgfn80v5vvdhuwn30wztyrczxsyj46ngpp2ryw36az6vlmlle8xns5k6pdlkgycr27naa2hpn3wspuvsxv0yzz62",
        amount=1000000,
        memo=None,
    )
    out_1 = ZcashOrchardOutput(
        address="utest1rgn5dkcq9vcf3vr7el74m2p2lslfw9ndn9dqm44ram756f544fndvd82ecv37gkxuum8mr8yrtjlnjwumgn48qrqlhch4znnqselfr5j",
        amount=1000000,
        memo=None,
    )
    out_2 = ZcashOrchardOutput(
        address="utest15w5alyhzu2l4k9umc3zxkv4x5mdg3ass97pu7n29arwaxrgc2r7xct3d3j0w0p26mvqxgrku2203xvp9nkwvfgdf9cxmyxlkm5n5cclt",
        amount=1000000,
        memo=None,
    )
    out_3 = ZcashOrchardOutput(
        address="utest1ms4aqpys9vpqdh52cq9stgyuam0wgw7whjtp3xshly5xpnp0070jlvh8dh280vudhg845psrdsx6zv8yvkju9v62cqtg8x8xcv2dxp4a",
        amount=1000000,
        memo=None,
    )
    out_4 = ZcashOrchardOutput(
        address="utest1lqcxy5sleh0dsdgxefj3jpehkwugxdvmfmemswa0xns3thhq5f2tuydl649utcktpydlttydnamprk3ddm22wszmcpzt608jws9s02nu",
        amount=1000000,
        memo=None,
    )
    out_5 = ZcashOrchardOutput(
        address="utest1jdqlx5evfxs65f05kgjdk9gtselavgredtg2kd4pzyf435hwfv250gel6k5hqhsx6rjsl2fauv8s4as7hy9fm2g7kd5vte834qyyupw9",
        amount=1000000,
        memo=None,
    )
    out_6 = ZcashOrchardOutput(
        address="utest19d9xjz0wu73u6h245c3v6j0wv3657akg0qvj0x45cars0dgl7vzdwa3dkm5zhsvgsas4z3wd79ua0ayl0nlcsfgpn0zawmqnlualld52",
        amount=1000000,
        memo=None,
    )
    out_7 = ZcashOrchardOutput(
        address="utest17rr4l9yjvk6le0aqa4vt0aauudhe07tvslhuvhmcds2jnklzx02hn0uw0xegs6ekgnu0ulyeqs6shjzepl2jemuesxpllmuj2gezg4zv",
        amount=1000000,
        memo=None,
    )
    anchor = bytes.fromhex("91513dfdbb4453c947bca9d704c3284ce40378e8732b250e9ff2386efb7e493c")
    expected_shielding_seed = bytes.fromhex("6b5186c0b2a8800f664effb57eaf17f81b2176283cc62832a5a64d578f1772f8")
    expected_sighash = bytes.fromhex("8b308b012587423557513fb16e33c80c838d87e8f41ce665af4bc44c591854fb")
    expected_serialized_tx = bytes.fromhex("050000800a27a726b4d0d6c200000000000000000000000008")

    with client:
        client.set_expected_responses(
            [
                request_orchard_input(0),
                request_orchard_input(1),
                request_orchard_input(2),
                request_orchard_input(3),
                request_orchard_input(4),
                request_orchard_input(5),
                request_orchard_input(6),
                request_orchard_input(7),
                request_orchard_output(0),
                ButtonRequest(code=B.ConfirmOutput),
                request_orchard_output(1),
                ButtonRequest(code=B.ConfirmOutput),
                request_orchard_output(2),
                ButtonRequest(code=B.ConfirmOutput),
                request_orchard_output(3),
                ButtonRequest(code=B.ConfirmOutput),
                request_orchard_output(4),
                ButtonRequest(code=B.ConfirmOutput),
                request_orchard_output(5),
                ButtonRequest(code=B.ConfirmOutput),
                request_orchard_output(6),
                ButtonRequest(code=B.ConfirmOutput),
                request_orchard_output(7),
                ButtonRequest(code=B.ConfirmOutput),
                ButtonRequest(code=B.SignTx),
                request_no_op(),  # shielding seed
                request_orchard_input(5),
                request_orchard_output(5),
                request_orchard_input(1),
                request_orchard_output(4),
                request_orchard_input(2),
                request_orchard_output(2),
                request_orchard_input(6),
                request_orchard_output(7),
                request_orchard_input(4),
                request_orchard_output(3),
                request_orchard_input(3),
                request_orchard_output(1),
                request_orchard_input(7),
                request_orchard_output(6),
                request_orchard_input(0),
                request_orchard_output(0),
                request_no_op(),  # returns o-signature of o-input 5 in action 0
                request_no_op(),  # returns o-signature of o-input 1 in action 1
                request_no_op(),  # returns o-signature of o-input 2 in action 2
                request_no_op(),  # returns o-signature of o-input 6 in action 3
                request_no_op(),  # returns o-signature of o-input 4 in action 4
                request_no_op(),  # returns o-signature of o-input 3 in action 5
                request_no_op(),  # returns o-signature of o-input 7 in action 6
                request_finished(),  # returns o-signature of o-input 0 in action 7
            ]
        )

        protocol = zcash.sign_tx(
            client,
            inputs=[inp_0, inp_1, inp_2, inp_3, inp_4, inp_5, inp_6, inp_7],
            outputs=[out_0, out_1, out_2, out_3, out_4, out_5, out_6, out_7],
            coin_name="Zcash Testnet",
            z_address_n=parse_path("m/32h/1h/0h"),
            anchor=anchor,
        )
        
        shielding_seed = next(protocol)
        assert shielding_seed == expected_shielding_seed
        sighash = next(protocol)
        assert sighash == expected_sighash
        signatures, serialized_tx = next(protocol)
        assert serialized_tx == expected_serialized_tx
        assert signatures == {
            ZcashSignatureType.TRANSPARENT: [],
            ZcashSignatureType.ORCHARD_SPEND_AUTH: {
                0: bytes.fromhex("cb4b6dbba23df3bf797867cadd324c8b7fc673b32c1ae1e9868281b70a2c412e0e8170834722103cf9a2262eee4c0be10722f1da8e3d3ad708713a5fa4492528"),
                1: bytes.fromhex("2ece02958aacff29a90f07654e0cb0dd1afee035c255a1ee9f30ee56d66f560c3a261c2c1f4738ca752409fab158776e537b9ae15057b4af5c2d651c9a22573b"),
                2: bytes.fromhex("d9622a17dc2e36b080cbc38ff0ac862bd71d2d57f6e76467836dbaea0855fb1b6ecbbb23102589508f836cdff611d00a726da43a9d60dae7e8863674b1afa605"),
                3: bytes.fromhex("c7d832d5df8520674a19b5397aefc4de9f57651afe7e076514a8d44e75e3e9a7086b11150b5565adfefc3c09347ab5413508a0008878fdd78be5061c7c15aa00"),
                4: bytes.fromhex("c57bf94dd38300b074cc9ccdae2c5f22d0c360166fc64f35905740613ffbaabae06199a65148e8a2b89926cf965290b1770ca0b7d824747c2ad0397d9e1cbe34"),
                5: bytes.fromhex("c515cd9891cba0909c801c9ddccf2d2e84864ffc023f804b5773b176d47b55993490c128ab7fc3a05bd5e61610a962264a4582d3f8479535952b9dd19d992729"),
                6: bytes.fromhex("102ecf29217dde10656dafc6d28faab65876aa9749d78f1c0cf1abfd1582c8bb58fa575d9e5054d9801ae0ecf1044ccda8ef63c612e5c2d3d5aad71b4cff9409"),
                7: bytes.fromhex("4711debbde8ff3c9746fe2a7bd35cd5630f5f3c6aa44bc46b7593cdc0cd89c8bf8b973ef7f07afbe7287821ec59c9c08e1a8ea2936d5799546c5630cb494ab1a"),
            },
        }

        # Accepted by network as fb5418594cc44baf65e61cf4e8878d830cc8336eb13f515735428725018b308b


def test_z2t(client: Client) -> None:
    # note 7eef85fc66c55557f6356dce9ecff03eebc4abe4b52a4f7ad0c41683d0427e32
    inp_0 = ZcashOrchardInput(
        recipient=bytes.fromhex("44a1a2b0e129b57e02d7cca0c0d666bac7de69f113c26e579c628545d58bf798e667b21ad7bcdd81e13914"),
        value=1000000,
        rho=bytes.fromhex("48d43a90616f6250746b826115215685bf5b93ba4fcf108410de1c6a6508af22"),
        rseed=bytes.fromhex("b3773c07b10a2d1cb6f904ea41d002c17f05b494601ccafdff3ceafd977bd9c0"),
    )
    
    out_0 = TxOutputType(
        address_n=parse_path("m/44h/1h/0h/0/0"),
        amount=990000,
        script_type=OutputScriptType.PAYTOADDRESS,
    )
    anchor = bytes.fromhex("91513dfdbb4453c947bca9d704c3284ce40378e8732b250e9ff2386efb7e493c")
    expected_shielding_seed = bytes.fromhex("30f5f6303f6999631ef505f02c8cdf38cd77853a0b3a7be25e87afa5fc3b6800")
    expected_sighash = bytes.fromhex("5248681d3f6f5af738c9a0a21ada818497ebe99b2187156e161e94fb5bda263b")
    expected_serialized_tx = bytes.fromhex("050000800a27a726b4d0d6c200000000000000000001301b0f00000000001976a914a579388225827d9f2fe9014add644487808c695d88ac000002")

    with client:
        client.set_expected_responses(
            [
                request_orchard_input(0),
                request_output(0),
                ButtonRequest(code=B.ConfirmOutput),
                ButtonRequest(code=B.SignTx),
                request_no_op(),  # shielding seed
                request_orchard_input(0),
                request_output(0),
                request_finished(),  # returns o-signature of o-input 0 in action 1
            ]
        )

        protocol = zcash.sign_tx(
            client,
            inputs=[inp_0],
            outputs=[out_0],
            coin_name="Zcash Testnet",
            z_address_n=parse_path("m/32h/1h/0h"),
            anchor=anchor,
        )
        
        shielding_seed = next(protocol)
        assert shielding_seed == expected_shielding_seed
        sighash = next(protocol)
        assert sighash == expected_sighash
        signatures, serialized_tx = next(protocol)
        assert serialized_tx == expected_serialized_tx
        assert signatures == {
            ZcashSignatureType.TRANSPARENT: [],
            ZcashSignatureType.ORCHARD_SPEND_AUTH: {
                1: bytes.fromhex("56aeef90fdcfe24327e22e21dbf6553ac79c199e94917715748113fd584ce90228e95fc700028272659b63846c98b4386124789281b284a18f7c50bc140e9c21"),
            },
        }

        # Accepted by network as 3b26da5bfb941e166e1587219be9eb978481da1aa2a0c938f75a6f3f1d684852


