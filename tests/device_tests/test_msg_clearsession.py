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
from trezorlib.btc import get_public_node
from trezorlib.tools import parse_path


@pytest.mark.skip_ui
@pytest.mark.setup_client(pin=True, passphrase=True)
def test_clear_session(client):
    if client.features.model == "1":
        # TODO: I'm pretty sure @matejcik won't like this, but I can't remember how to do this properly
        init_responses = [
            proto.PinMatrixRequest(),
            proto.PassphraseRequest(),
        ]
    else:
        init_responses = [
            proto.PassphraseRequest(),
        ]
    cached_responses = [
        proto.ButtonRequest(code=proto.ButtonRequestType.PublicKey),
        proto.PublicKey(),
    ]

    with client:
        client.set_expected_responses(init_responses + cached_responses)
        assert (
            get_public_node(
                client, parse_path("44'/0'/0'"), show_display=True
            ).node.public_key.hex()
            == "03c8166eb40ac84088b618ec07c7cebadacee31c5f5b04a1e8c2a2f3e748eb2cdd"
        )

    with client:
        # pin and passphrase are cached
        client.set_expected_responses(cached_responses)
        assert (
            get_public_node(
                client, parse_path("44'/0'/0'"), show_display=True
            ).node.public_key.hex()
            == "03c8166eb40ac84088b618ec07c7cebadacee31c5f5b04a1e8c2a2f3e748eb2cdd"
        )

    client.clear_session()

    # session cache is cleared
    with client:
        client.set_expected_responses(init_responses + cached_responses)
        assert (
            get_public_node(
                client, parse_path("44'/0'/0'"), show_display=True
            ).node.public_key.hex()
            == "03c8166eb40ac84088b618ec07c7cebadacee31c5f5b04a1e8c2a2f3e748eb2cdd"
        )

    with client:
        # pin and passphrase are cached
        client.set_expected_responses(cached_responses)
        assert (
            get_public_node(
                client, parse_path("44'/0'/0'"), show_display=True
            ).node.public_key.hex()
            == "03c8166eb40ac84088b618ec07c7cebadacee31c5f5b04a1e8c2a2f3e748eb2cdd"
        )
