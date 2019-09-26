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

SLOTS_TO_TEST = [(1), (2), (3), (4), (5), (6), (7), (8), (9), (10)]


@pytest.mark.skip_t1  # T1 support is not planned
@pytest.mark.beam
class TestBeamGenerateNonce(TrezorTest):
    @pytest.mark.parametrize("slot", SLOTS_TO_TEST)
    def test_generate_nonce(self, client, slot):
        self.setup_mnemonic_allallall()

        expected_responses = [messages.BeamECCPoint()]

        with client:
            client.set_expected_responses(expected_responses)
            _ = beam.generate_nonce(client, slot)


@pytest.mark.skip_t1  # T1 support is not planned
@pytest.mark.beam
class TestBeamGetNonceImage(TrezorTest):
    @pytest.mark.parametrize("slot", SLOTS_TO_TEST)
    def test_get_nonce_image(self, client, slot):
        self.setup_mnemonic_allallall()

        expected_responses = [
            messages.BeamECCPoint(),
            messages.BeamECCPoint(),
            messages.BeamECCPoint(),
            messages.BeamECCPoint(),
        ]

        with client:
            client.set_expected_responses(expected_responses)
            image1 = beam.get_nonce_image(client, slot)
            image2 = beam.get_nonce_image(client, slot)
            assert image1.x.hex() == image2.x.hex()
            assert image1.y == image2.y

            # Generate new nonce and check new one is not the same
            image3 = beam.generate_nonce(client, slot)
            assert not (image3.x.hex() == image2.x.hex())
            # But next one is the same
            image4 = beam.get_nonce_image(client, slot)
            assert image3.x.hex() == image4.x.hex()
            assert image3.y == image4.y
