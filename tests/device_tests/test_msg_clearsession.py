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

from trezorlib import messages as proto

from .common import TrezorTest


@pytest.mark.skip_t2
class TestMsgClearsession(TrezorTest):
    @pytest.mark.setup_client(pin=True, passphrase=True)
    def test_clearsession(self, client):
        with client:
            client.set_expected_responses(
                [
                    proto.ButtonRequest(code=proto.ButtonRequestType.ProtectCall),
                    proto.PinMatrixRequest(),
                    proto.PassphraseRequest(),
                    proto.Success(),
                ]
            )
            res = client.ping(
                "random data",
                button_protection=True,
                pin_protection=True,
                passphrase_protection=True,
            )
            assert res == "random data"

        with client:
            # pin and passphrase are cached
            client.set_expected_responses(
                [
                    proto.ButtonRequest(code=proto.ButtonRequestType.ProtectCall),
                    proto.Success(),
                ]
            )
            res = client.ping(
                "random data",
                button_protection=True,
                pin_protection=True,
                passphrase_protection=True,
            )
            assert res == "random data"

        client.clear_session()

        # session cache is cleared
        with client:
            client.set_expected_responses(
                [
                    proto.ButtonRequest(code=proto.ButtonRequestType.ProtectCall),
                    proto.PinMatrixRequest(),
                    proto.PassphraseRequest(),
                    proto.Success(),
                ]
            )
            res = client.ping(
                "random data",
                button_protection=True,
                pin_protection=True,
                passphrase_protection=True,
            )
            assert res == "random data"

        with client:
            # pin and passphrase are cached
            client.set_expected_responses(
                [
                    proto.ButtonRequest(code=proto.ButtonRequestType.ProtectCall),
                    proto.Success(),
                ]
            )
            res = client.ping(
                "random data",
                button_protection=True,
                pin_protection=True,
                passphrase_protection=True,
            )
            assert res == "random data"
