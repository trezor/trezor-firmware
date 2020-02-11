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

from trezorlib import messages
from trezorlib.btc import get_public_node
from trezorlib.tools import parse_path

ADDRESS_N = parse_path("44'/0'/0'")
XPUB = "xpub6BiVtCpG9fQPxnPmHXG8PhtzQdWC2Su4qWu6XW9tpWFYhxydCLJGrWBJZ5H6qTAHdPQ7pQhtpjiYZVZARo14qHiay2fvrX996oEP42u8wZy"


@pytest.mark.skip_ui
@pytest.mark.setup_client(pin=True, passphrase=True)
def test_clear_session(client):
    if client.features.model == "1":
        init_responses = [messages.PinMatrixRequest(), messages.PassphraseRequest()]
    else:
        init_responses = [messages.PassphraseRequest()]

    cached_responses = [messages.PublicKey()]

    with client:
        client.set_expected_responses(init_responses + cached_responses)
        assert get_public_node(client, ADDRESS_N).xpub == XPUB

    with client:
        # pin and passphrase are cached
        client.set_expected_responses(cached_responses)
        assert get_public_node(client, ADDRESS_N).xpub == XPUB

    client.clear_session()

    # session cache is cleared
    with client:
        client.set_expected_responses(init_responses + cached_responses)
        assert get_public_node(client, ADDRESS_N).xpub == XPUB

    with client:
        # pin and passphrase are cached
        client.set_expected_responses(cached_responses)
        assert get_public_node(client, ADDRESS_N).xpub == XPUB
