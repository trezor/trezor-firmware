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

VALID_VECTORS = [
    (0, 0, "88b528eecb5ee5ae81e56e2105aca06997761c9cd2e566b25eaee1951be26688", 1),
    (0, 1, "53839a38c1089e28e901279266cff2da921ca82ed39c6ac0261a039157754e40", 1),
    (0, 8, "a3378664f9ada1a32cf860076ec6110621c7430d9b04316a20b56ced6fd73546", 1),
    (1, 1, "da2d246d99860617bd37755605f0584de6094b437efb4931ec20cf85b62631a5", 0),
    (1, 8, "54158bdbeef7292b96d5ea57b2eebc3ba6c8d4a16cfeb6cd75354e8497d009b8", 1),
    (2, 8, "bfb3e6e6eb8ee2b686aaa6a056fa2670a5c49d76583eb05fb84d9c5ab7227c71", 0),
    (3, 0, "22e6e269fb26638d8501583d5a7c0c8051315f9576174cc6f64dacfe9a01ef7f", 0),
    (3, 3, "392b73f534c490f614c36a3ad738a10b2cc4b08543e6250a2b2927d1c5ffa4ba", 1),
    (4, 4, "e5c551250ccb2dfbd11b5d38eae670d0476909acb7d1955c78c53647dd5de3e9", 0),
    (5, 2, "269c9a18d3a8f5acf4036a711e41cf7c5071aceac1fe95666040369a3311ac71", 0),
    (10, 3, "706bc1d21de9d4fdf4daef73b7774cb7e869e454a7776d8116c0ce86f9427577", 0),
]


@pytest.mark.skip_t1  # T1 support is not planned
@pytest.mark.beam
class TestBeamGetPublicKey(TrezorTest):
    @pytest.mark.parametrize(
        "idx, sub_idx, expected_pk_x, expected_pk_y", VALID_VECTORS
    )
    def test_generate_pk(self, client, idx, sub_idx, expected_pk_x, expected_pk_y):
        self.setup_mnemonic_allallall()

        expected_responses = [messages.BeamECCPoint()]

        with self.client:
            self.client.set_expected_responses(expected_responses)
            pk = beam.get_public_key(self.client, idx, sub_idx, False)
            assert pk.x.hex() == expected_pk_x
            assert int(pk.y) == expected_pk_y

    @pytest.mark.parametrize(
        "idx, sub_idx, expected_pk_x, expected_pk_y", VALID_VECTORS
    )
    def test_generate_pk_with_display(
        self, client, idx, sub_idx, expected_pk_x, expected_pk_y
    ):
        self.setup_mnemonic_allallall()

        expected_responses = [
            messages.ButtonRequest(code=messages.ButtonRequestType.PublicKey),
            messages.ButtonRequest(code=messages.ButtonRequestType.PublicKey),
            messages.BeamECCPoint(),
        ]

        def input_flow():
            yield
            self.client.debug.press_yes()
            yield
            self.client.debug.press_yes()

        with self.client:
            self.client.set_expected_responses(expected_responses)
            self.client.set_input_flow(input_flow)
            pk = beam.get_public_key(self.client, idx, sub_idx, True)
            assert pk.x.hex() == expected_pk_x
            assert int(pk.y) == expected_pk_y
