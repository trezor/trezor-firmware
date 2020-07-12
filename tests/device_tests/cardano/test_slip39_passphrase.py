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

from trezorlib import btc, cardano, messages, tools

from ...common import MNEMONIC_SLIP39_BASIC_20_3of6


@pytest.mark.altcoin
@pytest.mark.cardano
@pytest.mark.skip_t1  # T1 support is not planned
@pytest.mark.skip_ui
@pytest.mark.setup_client(mnemonic=MNEMONIC_SLIP39_BASIC_20_3of6, passphrase=True)
def test_single_passphrase_entry(client):
    # try empty passphrase
    with client:
        client.use_passphrase("")
        client.set_expected_responses(
            [messages.PassphraseRequest(), messages.CardanoAddress()]
        )
        address_a = cardano.get_address(client, tools.parse_path("m/44'/1815'/0'/0/0"))

    client.clear_session()

    # in a new session, unlock non-Cardano first
    with client:
        client.use_passphrase("TREZOR")
        client.set_expected_responses(
            [messages.PassphraseRequest(), messages.Address()]
        )
        # invoke passphrase prompt
        btc.get_address(client, "Testnet", tools.parse_path("m/44'/1'/0'/0/0"))

    with client:
        # Cardano should not ask for passphrase again
        client.set_expected_responses([messages.CardanoAddress()])
        address_b = cardano.get_address(client, tools.parse_path("m/44'/1815'/0'/0/0"))
        # but it should be using the previously entered passphrase
        assert address_a != address_b
