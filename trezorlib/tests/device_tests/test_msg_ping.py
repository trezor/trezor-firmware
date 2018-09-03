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

from trezorlib import messages as proto

from .common import TrezorTest


@pytest.mark.skip_t2
class TestMsgPing(TrezorTest):
    def test_ping(self):
        self.setup_mnemonic_pin_passphrase()

        with self.client:
            self.client.set_expected_responses([proto.Success()])
            res = self.client.ping("random data")
            assert res == "random data"

        with self.client:
            self.client.set_expected_responses(
                [
                    proto.ButtonRequest(code=proto.ButtonRequestType.ProtectCall),
                    proto.Success(),
                ]
            )
            res = self.client.ping("random data", button_protection=True)
            assert res == "random data"

        with self.client:
            self.client.set_expected_responses(
                [proto.PinMatrixRequest(), proto.Success()]
            )
            res = self.client.ping("random data", pin_protection=True)
            assert res == "random data"

        with self.client:
            self.client.set_expected_responses(
                [proto.PassphraseRequest(), proto.Success()]
            )
            res = self.client.ping("random data", passphrase_protection=True)
            assert res == "random data"

    def test_ping_caching(self):
        self.setup_mnemonic_pin_passphrase()

        with self.client:
            self.client.set_expected_responses(
                [
                    proto.ButtonRequest(code=proto.ButtonRequestType.ProtectCall),
                    proto.PinMatrixRequest(),
                    proto.PassphraseRequest(),
                    proto.Success(),
                ]
            )
            res = self.client.ping(
                "random data",
                button_protection=True,
                pin_protection=True,
                passphrase_protection=True,
            )
            assert res == "random data"

        with self.client:
            # pin and passphrase are cached
            self.client.set_expected_responses(
                [
                    proto.ButtonRequest(code=proto.ButtonRequestType.ProtectCall),
                    proto.Success(),
                ]
            )
            res = self.client.ping(
                "random data",
                button_protection=True,
                pin_protection=True,
                passphrase_protection=True,
            )
            assert res == "random data"
