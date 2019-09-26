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
class TestBeamGetOwnerKeyMessage(TrezorTest):
    def test_get_owner_key(self, client):
        self.setup_mnemonic_pin_nopassphrase()

        pin = "1234"

        expected_responses = [
            messages.ButtonRequest(),
            messages.ButtonRequest(),
            messages.ButtonRequest(),
            messages.BeamOwnerKey(),
        ]

        def input_flow():
            self.client.debug.input(pin)
            yield
            self.client.debug.press_yes()
            yield
            self.client.debug.press_yes()
            yield
            self.client.debug.press_yes()

        with self.client:
            self.client.set_expected_responses(expected_responses)
            self.client.set_input_flow(input_flow)

            owner_key = beam.get_owner_key(self.client, True)
            assert (
                owner_key.key.decode("utf-8")
                == "i785WRTwjoq1CmHBAXnogoYAv1GtcjxCd0aPbt2Dg5SrluylUtUzNu9YG0bhfG+j3MK7cvGLpqnj/AD5jubFk7kfUFcemCuihCqwsKb42Fc9XveGiAZHmOcr9I1kwQIb68+jNxA8Yy+iTTy2\n"
            )
