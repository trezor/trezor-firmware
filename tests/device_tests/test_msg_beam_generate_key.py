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

from trezorlib import beam, messages

from .common import TrezorTest


@pytest.mark.skip_t1  # T1 support is not planned
@pytest.mark.beam
class TestBeamGenerateKey(TrezorTest):
    @pytest.mark.parametrize(
        "idx, type, sub_idx, value, expected_key_image_x, expected_key_image_y",
        [
            (
                0,
                0,
                0,
                0,
                "cd42fb9a8635d3db969026c0980758cca79e019d706bc7eab447594db0d55a14",
                1,
            ),
            (
                0,
                0,
                0,
                1,
                "af37e62530b9ebb0244ebb85723d0a05217c1db9171d0efa0f363d9740b026a0",
                1,
            ),
            (
                0,
                0,
                1,
                0,
                "6707ffe74a80747d399ea07edb5bc8c9602143a4353255acbe05c304fd2b2e84",
                0,
            ),
            (
                0,
                0,
                1,
                1,
                "c100049030ee19060a757aed808239b1d7e2dec147d7fde45ac12c4864c8ed2c",
                0,
            ),
            (
                0,
                1,
                0,
                0,
                "a07320264c168029fb2cbb6b04a0f7580c35edfccb6698bc21d45f5cb7bf40d4",
                1,
            ),
            (
                0,
                2,
                0,
                0,
                "e47ea24fc36b6fd0dfa5466460d4dd0c7704d1c4b7a6e897915b5981736702e1",
                1,
            ),
            (
                0,
                2,
                3,
                0,
                "6fcfecbe68f170fbead504785cb7ef590c2a64d1168560aa4dadb32b51eecc64",
                1,
            ),
            (
                1,
                0,
                0,
                0,
                "0d375bcc3f316ec0324b3d2a70a6bca52da2849744244595369f090484636a97",
                0,
            ),
            (
                1,
                2,
                3,
                4,
                "c769ac4cdcd4bc15e9d6c431d9fb05c1b52ee7296566fdce7b6536906f2358b8",
                1,
            ),
            (
                4,
                3,
                2,
                1,
                "f572003c7c99b8e5443b91ac1cba2762c1614a3e53606629e6fb4ab22e26ea7a",
                1,
            ),
        ],
    )
    def test_generate_key(
        self, idx, type, sub_idx, value, expected_key_image_x, expected_key_image_y
    ):
        self.setup_mnemonic_allallall()
        is_coin_key = True

        expected_responses = [messages.BeamECCPoint()]

        with self.client:
            self.client.set_expected_responses(expected_responses)

            generated_key = beam.generate_key(
                self.client, idx, type, sub_idx, value, is_coin_key
            )
            assert generated_key.x.hex() == expected_key_image_x
            assert int(generated_key.y) == expected_key_image_y
