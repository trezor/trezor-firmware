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

KERNEL_PARAMS = {
    "fee": 1,
    "commitment": {
        "x": "0x12abcdef12abcdef12abcdef12abcdef12abcdef12abcdef12abcdef12abcdef",
        "y": 1,
    },
    "min_height": 1,
    "max_height": 5,
    "asset_emission": 2,
    "hash_lock": "0x12abcdef12abcdef12abcdef12abcdef12abcdef12abcdef12abcdef12abcdef",
    "multisig": {
        "nonce": {
            "x": "0x12abcdef12abcdef12abcdef12abcdef12abcdef12abcdef12abcdef12abcdef",
            "y": 1,
        },
        "excess": {
            "x": "0x12abcdef12abcdef12abcdef12abcdef12abcdef12abcdef12abcdef12abcdef",
            "y": 1,
        },
    },
}


@pytest.mark.skip_t1  # T1 support is not planned
@pytest.mark.beam
class TestBeamSignTxMessage(TrezorTest):
    @pytest.mark.parametrize(
        "inputs, outputs, offset_sk, nonce_slot",
        [
            (
                # Inputs
                [
                    {"idx": 1, "type": 1, "sub_idx": 1, "value": 2},
                    {"idx": 2, "type": 2, "sub_idx": 2, "value": 5},
                ],
                # Outputs
                [{"idx": 3, "type": 3, "sub_idx": 3, "value": 3}],
                # Offset sk
                "0x12abcdef12abcdef12abcdef12abcdef12abcdef12abcdef12abcdef12abcdef",
                # Nonce slot
                2,
            ),
            (
                # Inputs
                [
                    {"idx": 1, "type": 1, "sub_idx": 1, "value": 2},
                    {"idx": 2, "type": 2, "sub_idx": 2, "value": 5},
                ],
                # Outputs
                [{"idx": 3, "type": 3, "sub_idx": 3, "value": 20}],
                # Offset sk
                "0x12abcdef12abcdef12abcdef12abcdef12abcdef12abcdef12abcdef12abcdef",
                # Nonce slot
                1,
            ),
        ],
    )
    def test_sign_tx(self, client, inputs, outputs, offset_sk, nonce_slot):
        self.setup_mnemonic_allallall()

        inputs = [beam.create_kidv(input) for input in inputs]
        outputs = [beam.create_kidv(output) for output in outputs]

        kernel_params = beam.create_kernel_params(KERNEL_PARAMS)

        expected_responses = [
            messages.ButtonRequest(),
            messages.BeamSignedTransaction(),
        ]

        def input_flow():
            yield
            self.client.debug.press_yes()

        with self.client:
            self.client.set_expected_responses(expected_responses)
            self.client.set_input_flow(input_flow)
            _ = beam.sign_tx(
                self.client, inputs, outputs, offset_sk, nonce_slot, kernel_params
            )
