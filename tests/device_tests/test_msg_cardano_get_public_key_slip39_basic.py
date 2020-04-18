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
from trezorlib.tools import parse_path

from ..common import MNEMONIC_SLIP39_BASIC_20_3of6


@pytest.mark.altcoin
@pytest.mark.cardano
@pytest.mark.skip_t1  # T1 support is not planned
@pytest.mark.skip_ui
@pytest.mark.setup_client(mnemonic=MNEMONIC_SLIP39_BASIC_20_3of6, passphrase=True)
@pytest.mark.parametrize(
    "path,public_key,chain_code",
    [
        (
            "m/44'/1815'/0'/0/0",
            "bc043d84b8b891d49890edb6aced6f2d78395f255c5b6aea8878b913f83e8579",
            "dc3f0d2b5cccb822335ef6213fd133f4ca934151ec44a6000aee43b8a101078c",
        ),
        (
            "m/44'/1815'/0'/0/1",
            "24c4fe188a39103db88818bc191fd8571eae7b284ebcbdf2462bde97b058a95c",
            "6f7a744035f4b3ddb8f861c18446169643cc3ae85e271b4b4f0eda05cf84c65b",
        ),
        (
            "m/44'/1815'/0'/0/2",
            "831a63d381a8dab1e6e1ee991a4300fc70687aae5f97f4fcf92ed1b6c2bd99de",
            "672d6af4707aba201b7940231e83dd357f92f8851b3dfdc224ef311e1b64cdeb",
        ),
    ],
)
def test_cardano_get_public_key(client, path, public_key, chain_code):
    # enter passphrase
    assert client.features.passphrase_protection is True
    client.use_passphrase("TREZOR")

    key = get_public_key(client, parse_path(path))

    assert key.node.public_key.hex() == public_key
    assert key.node.chain_code.hex() == chain_code
    assert key.xpub == public_key + chain_code
