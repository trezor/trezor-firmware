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

from trezorlib.cardano import get_public_key
from trezorlib.exceptions import TrezorFailure
from trezorlib.messages import CardanoDerivationType as D
from trezorlib.tools import parse_path

from ...common import MNEMONIC_SLIP39_BASIC_20_3of6

pytestmark = [
    pytest.mark.altcoin,
    pytest.mark.cardano,
    pytest.mark.skip_t1,
]

ADDRESS_N = parse_path("m/1852'/1815'/0'")


def test_bad_session(client):
    client.init_device(new_session=True)
    with pytest.raises(TrezorFailure, match="not enabled"):
        get_public_key(client, ADDRESS_N, derivation_type=D.ICARUS)

    client.init_device(new_session=True, derive_cardano=False)
    with pytest.raises(TrezorFailure, match="not enabled"):
        get_public_key(client, ADDRESS_N, derivation_type=D.ICARUS)


def test_ledger_available_always(client):
    client.init_device(new_session=True, derive_cardano=False)
    get_public_key(client, ADDRESS_N, derivation_type=D.LEDGER)

    client.init_device(new_session=True, derive_cardano=True)
    get_public_key(client, ADDRESS_N, derivation_type=D.LEDGER)


@pytest.mark.setup_client(mnemonic=MNEMONIC_SLIP39_BASIC_20_3of6)
@pytest.mark.parametrize("derivation_type", D)  # try ALL derivation types
def test_derivation_irrelevant_on_slip39(client, derivation_type):
    client.init_device(new_session=True, derive_cardano=False)
    pubkey = get_public_key(client, ADDRESS_N, derivation_type=D.ICARUS)
    test_pubkey = get_public_key(client, ADDRESS_N, derivation_type=derivation_type)
    assert pubkey == test_pubkey
