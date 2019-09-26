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
class TestBeamGenerateRangeproof(TrezorTest):
    @pytest.mark.parametrize(
        "idx, type, sub_idx, value, is_public",
        [
            (0, 0, 0, 5, True),
            (1, 0, 0, 8, True),
            (2, 1, 1, 3, True),
            (0, 0, 0, 4, False),
        ],
    )
    def test_generate_rangeproof(self, client, idx, type, sub_idx, value, is_public):
        self.setup_mnemonic_allallall()

        expected_responses = [messages.BeamRangeproofData()]

        with self.client:
            self.client.set_expected_responses(expected_responses)
            rp_data = beam.generate_rangeproof(
                self.client, idx, type, sub_idx, value, is_public
            )
            assert rp_data.is_public == is_public
