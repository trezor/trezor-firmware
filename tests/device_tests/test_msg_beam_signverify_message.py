# This file is part of the Trezor project.
#
# Copyright (C) 2012-2018 SatoshiLabs and contributors
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

from trezorlib import beam, messages

from .common import TrezorTest


@pytest.mark.skip_t1  # T1 support is not planned
@pytest.mark.beam
class TestBeamSignVerifyMessage(TrezorTest):
    @pytest.mark.parametrize(
        "kid_idx, kid_sub_idx, message, nonce_pub_x, nonce_pub_y, sign_k, expected_is_valid",
        [
            [
                0,
                0,
                "hello world",
                "94bb1f34c5e970136d4f1ff769e3332e4e5f430122ebe7e7720c754713adfab6",
                0,
                "9f01b0eb202cd0780e35f0cf20c06cd930af8bb55db9c9c3e2146f34de1239d9",
                True,
            ],
            [
                0,
                0,
                "hello world",
                "94bb1f34c5e970136d4f1ff769e3332e4e5f430122ebe7e7720c754713adfab6",
                1,
                "9f01b0eb202cd0780e35f0cf20c06cd930af8bb55db9c9c3e2146f34de1239d9",
                False,
            ],
            [
                0,
                1,
                "hello world",
                "39e2014221f59c4f887be7158df22ef996ff061b7411a6d915ac91dc5a336d4b",
                0,
                "a7b9447e39eb14e0c3167496ba53b3253918577c1c4bc0084fe8105ea6d520e5",
                True,
            ],
            [
                1,
                0,
                "hello world",
                "39e2014221f59c4f887be7158df22ef996ff061b7411a6d915ac91dc5a336d4b",
                0,
                "a7b9447e39eb14e0c3167496ba53b3253918577c1c4bc0084fe8105ea6d520e5",
                False,
            ],
            [
                5,
                2,
                "hello world",
                "fbf34c594f346f3937eb3306d70a0801d583c6c044311085f3a8f40b6195948a",
                0,
                "2da2b290d11892bf88c590dd507fffb2a7c6660f269f2ca54dc661eebc1c758e",
                True,
            ],
            [
                5,
                2,
                "hello, world",
                "fbf34c594f346f3937eb3306d70a0801d583c6c044311085f3a8f40b6195948a",
                0,
                "2da2b290d11892bf88c590dd507fffb2a7c6660f269f2ca54dc661eebc1c758e",
                False,
            ],
            [
                0,
                0,
                "hello world",
                "758ce1a21710733f5dbb45cf0247d1600b0e19a1a4197a8327b9878ae8adb6ff",
                1,
                "2f032c76a0ce00d8a4a5df48d5013c88878714e70facbfe6e76662eb45a75d61",
                True,
            ],
            [
                1,
                8,
                "hello from BEAM",
                "2a7b6b29252a13d6e06f92e3e25c783258749facbbcc994277bacbd6005adc03",
                1,
                "7b0f586f092602ee9d49c191300a2a4a1c1c8bbc8d343add4c0194597f94fe7f",
                True,
            ],
            [
                1,
                8,
                "hello from BEAM!",
                "2a7b6b29252a13d6e06f92e3e25c783258749facbbcc994277bacbd6005adc03",
                1,
                "7b0f586f092602ee9d49c191300a2a4a1c1c8bbc8d343add4c0194597f94fe7f",
                False,
            ],
            [
                4,
                4,
                "abcdefg",
                "cdf450609819f595e3b7c79d35ee48a0352f2999d1874258d31df57ba49b3aaf",
                1,
                "583a10b35cac6efca6ea4a9776b364f281cb1830ef09424d24bf2619c20f8141",
                True,
            ],
            [
                4,
                5,
                "abcdefg",
                "cdf450609819f595e3b7c79d35ee48a0352f2999d1874258d31df57ba49b3aaf",
                1,
                "583a10b35cac6efca6ea4a9776b364f281cb1830ef09424d24bf2619c20f8141",
                False,
            ],
        ],
    )
    def test_beam_verify_message_with_requested_pk_by_kid(
        self,
        client,
        kid_idx,
        kid_sub_idx,
        message,
        nonce_pub_x,
        nonce_pub_y,
        sign_k,
        expected_is_valid,
    ):
        self.setup_mnemonic_allallall()

        expected_responses_positive = [
            # Public Key
            messages.BeamECCPoint(),
            # Verify process
            messages.ButtonRequest(),
            messages.ButtonRequest(),
            messages.ButtonRequest(),
            messages.ButtonRequest(),
            messages.ButtonRequest(),
            messages.Success(),
        ]
        expected_responses_negative = [
            # Public Key
            messages.BeamECCPoint(),
            # Verify process
            messages.Failure(code=messages.FailureType.InvalidSignature),
        ]

        def input_flow():
            self.client.debug.press_yes()
            yield
            self.client.debug.press_yes()
            yield
            self.client.debug.press_yes()
            yield
            self.client.debug.press_yes()
            yield
            self.client.debug.press_yes()
            yield
            self.client.debug.press_yes()

        with self.client:
            if expected_is_valid:
                self.client.set_expected_responses(expected_responses_positive)
            else:
                self.client.set_expected_responses(expected_responses_negative)
            self.client.set_input_flow(input_flow)

            pk = beam.get_public_key(self.client, kid_idx, kid_sub_idx, False)
            is_verified = beam.verify_message(
                self.client, nonce_pub_x, nonce_pub_y, sign_k, pk.x.hex(), pk.y, message
            )
            assert is_verified == expected_is_valid

    @pytest.mark.parametrize(
        "message, nonce_pub_x, nonce_pub_y, sign_k, pk_x, pk_y, expected_is_valid",
        [
            [
                "hello world",
                "94bb1f34c5e970136d4f1ff769e3332e4e5f430122ebe7e7720c754713adfab6",
                0,
                "9f01b0eb202cd0780e35f0cf20c06cd930af8bb55db9c9c3e2146f34de1239d9",
                "88b528eecb5ee5ae81e56e2105aca06997761c9cd2e566b25eaee1951be26688",
                1,
                True,
            ],
            [
                "hello world",
                "39e2014221f59c4f887be7158df22ef996ff061b7411a6d915ac91dc5a336d4b",
                0,
                "a7b9447e39eb14e0c3167496ba53b3253918577c1c4bc0084fe8105ea6d520e5",
                "53839a38c1089e28e901279266cff2da921ca82ed39c6ac0261a039157754e40",
                1,
                True,
            ],
            [
                "hello world",
                "39e2014221f59c4f887be7158df22ef996ff061b7411a6d915ac91dc5a336d4b",
                0,
                "a7b9447e39eb14e0c3167496ba53b3253918577c1c4bc0084fe8105ea6d520e5",
                "53839a38c1089e28e901279266cff2da921ca82ed39c6ac0261a039157754e40",
                0,
                False,
            ],
            [
                "hello world",
                "848824bb7e3ee53ecc0d9ecdbacd8e7015d80ebaa3f50a0147d65a92e8d61894",
                0,
                "d6d4b41ba3c858d99bb454155b9e9d531c35fc8f1535807a38e9509cb7314a75",
                "269c9a18d3a8f5acf4036a711e41cf7c5071aceac1fe95666040369a3311ac71",
                0,
                True,
            ],
            [
                "hello world",
                "9f315b9105225a0493d072d345b0e9a96e7c68395f004676c508259a16ade81e",
                1,
                "3a303f731efb81d035cc98d835b66e109dd17921ec0e14091aecc72d64d7ab40",
                "88b528eecb5ee5ae81e56e2105aca06997761c9cd2e566b25eaee1951be26688",
                1,
                True,
            ],
            [
                "hello from BEAM",
                "50d1f214d345a0f9cab5f7299f8e300ff1ee7c1201646bd67132203526593263",
                0,
                "a49d590c6894f1675b5d6a43bb7845c9277d66d70c1114927a7870c6c6e95492",
                "54158bdbeef7292b96d5ea57b2eebc3ba6c8d4a16cfeb6cd75354e8497d009b8",
                1,
                True,
            ],
            [
                "abcdefg",
                "ec088ee2b66fab3b3c43337e8ad992dcc81e69a55f40b36b181a6899fc08a0f8",
                0,
                "177a773a6278a87f03606edb5237f83bd40ea2e2954649e20930c42eb4bd7f17",
                "e5c551250ccb2dfbd11b5d38eae670d0476909acb7d1955c78c53647dd5de3e9",
                0,
                True,
            ],
            [
                "abcdefg",
                "ec088ee2b66fab3b3c43337e8ad992dcc81e69a55f40b36b181a6899fc08a0f8",
                0,
                "177a773a6278a87f03606edb5237f83bd40ea2e2954649e20930c42eb4bd7f17",
                "f5c551250ccb2dfbd11b5d38eae670d0476909acb7d1955c78c53647dd5de3e9",
                0,
                False,
            ],
        ],
    )
    def test_beam_verify_message_with_defined_pk(
        self,
        client,
        message,
        nonce_pub_x,
        nonce_pub_y,
        sign_k,
        pk_x,
        pk_y,
        expected_is_valid,
    ):
        self.setup_mnemonic_allallall()

        expected_responses_positive = [
            # Verify process
            messages.ButtonRequest(),
            messages.ButtonRequest(),
            messages.ButtonRequest(),
            messages.ButtonRequest(),
            messages.ButtonRequest(),
            messages.Success(),
        ]
        expected_responses_negative = [
            # Verify process
            messages.Failure(code=messages.FailureType.InvalidSignature)
        ]

        def input_flow():
            self.client.debug.press_yes()
            yield
            self.client.debug.press_yes()
            yield
            self.client.debug.press_yes()
            yield
            self.client.debug.press_yes()
            yield
            self.client.debug.press_yes()
            yield
            self.client.debug.press_yes()

        with self.client:
            if expected_is_valid:
                self.client.set_expected_responses(expected_responses_positive)
            else:
                self.client.set_expected_responses(expected_responses_negative)
            self.client.set_input_flow(input_flow)

            is_verified = beam.verify_message(
                self.client, nonce_pub_x, nonce_pub_y, sign_k, pk_x, pk_y, message
            )
            assert is_verified == expected_is_valid

    @pytest.mark.parametrize(
        "kid_idx, kid_sub_idx, message",
        [
            [0, 0, "hello world"],
            [0, 1, "hello world"],
            [5, 2, "hello world"],
            [0, 0, "hello world"],
            [1, 8, "hello from BEAM"],
            [4, 4, "abcdefg"],
        ],
    )
    def test_beam_sign_message(self, client, kid_idx, kid_sub_idx, message):
        self.setup_mnemonic_allallall()

        expected_responses = [
            # Sign message
            messages.ButtonRequest(),
            messages.ButtonRequest(),
            # Signature
            messages.BeamSignature(),
            # Public Key
            messages.BeamECCPoint(),
            # Verify process
            messages.ButtonRequest(),
            messages.ButtonRequest(),
            messages.ButtonRequest(),
            messages.ButtonRequest(),
            messages.ButtonRequest(),
            messages.Success(),
        ]

        def input_flow():
            self.client.debug.press_yes()
            yield
            self.client.debug.press_yes()
            yield
            self.client.debug.press_yes()
            yield
            self.client.debug.press_yes()
            yield
            self.client.debug.press_yes()
            yield
            self.client.debug.press_yes()
            yield
            self.client.debug.press_yes()
            yield
            self.client.debug.press_yes()

        with self.client:
            self.client.set_expected_responses(expected_responses)
            self.client.set_input_flow(input_flow)

            signature = beam.sign_message(self.client, message, kid_idx, kid_sub_idx)
            pk = beam.get_public_key(self.client, kid_idx, kid_sub_idx, False)
            is_verified = beam.verify_message(
                self.client,
                signature.nonce_pub.x.hex(),
                signature.nonce_pub.y,
                signature.sign_k.hex(),
                pk.x.hex(),
                pk.y,
                message,
            )
            assert is_verified
