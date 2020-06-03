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

from trezorlib.cardano import get_address, get_public_key
from trezorlib.tools import parse_path

from ...common import MNEMONIC12, MNEMONIC_SLIP39_BASIC_20_3of6

pytestmark = [
    pytest.mark.altcoin,
    pytest.mark.cardano,
    pytest.mark.skip_t1,
]


def with_mnemonic(mnemo):
    return pytest.mark.setup_client(passphrase=True, mnemonic=mnemo)


@pytest.mark.skip_ui
@pytest.mark.parametrize(
    "path, expected_address, passphrase",
    [
        pytest.param(
            "m/44'/1815'/0'/0/0",
            "Ae2tdPwUPEZLCq3sFv4wVYxwqjMH2nUzBVt1HFr4v87snYrtYq3d3bq2PUQ",
            "",
            marks=with_mnemonic(MNEMONIC12),
        ),
        pytest.param(
            "m/44'/1815'/0'/0/1",
            "Ae2tdPwUPEZEY6pVJoyuNNdLp7VbMB7U7qfebeJ7XGunk5Z2eHarkcN1bHK",
            "",
            marks=with_mnemonic(MNEMONIC12),
        ),
        pytest.param(
            "m/44'/1815'/0'/0/2",
            "Ae2tdPwUPEZ3gZD1QeUHvAqadAV59Zid6NP9VCR9BG5LLAja9YtBUgr6ttK",
            "",
            marks=with_mnemonic(MNEMONIC12),
        ),
        pytest.param(
            "m/44'/1815'/0'/0/0",
            "Ae2tdPwUPEYxF9NAMNdd3v2LZoMeWp7gCZiDb6bZzFQeeVASzoP7HC4V9s6",
            "TREZOR",
            marks=with_mnemonic(MNEMONIC_SLIP39_BASIC_20_3of6),
        ),
        pytest.param(
            "m/44'/1815'/0'/0/1",
            "Ae2tdPwUPEZ1TjYcvfkWAbiHtGVxv4byEHHZoSyQXjPJ362DifCe1ykgqgy",
            "TREZOR",
            marks=with_mnemonic(MNEMONIC_SLIP39_BASIC_20_3of6),
        ),
        pytest.param(
            "m/44'/1815'/0'/0/2",
            "Ae2tdPwUPEZGXmSbda1kBNfyhRQGRcQxJFdk7mhWZXAGnapyejv2b2U3aRb",
            "TREZOR",
            marks=with_mnemonic(MNEMONIC_SLIP39_BASIC_20_3of6),
        ),
    ],
)
def test_cardano_get_address(client, path, expected_address, passphrase):
    client.use_passphrase(passphrase)
    address = get_address(client, parse_path(path))
    assert address == expected_address


@pytest.mark.skip_ui
@pytest.mark.parametrize(
    "path, public_key, chain_code, passphrase",
    [
        pytest.param(
            "m/44'/1815'/0'",
            "c0fce1839f1a84c4e770293ac2f5e0875141b29017b7f56ab135352d00ad6966",
            "07faa161c9f5464315d2855f70fdf1431d5fa39eb838767bf17b69772137452f",
            "",
        ),
        pytest.param(
            "m/44'/1815'/1'",
            "ea5dde31b9f551e08a5b6b2f98b8c42c726f726c9ce0a7072102ead53bd8f21e",
            "70f131bb799fd659c997221ad8cae7dcce4e8da701f8101cf15307fd3a3712a1",
            "",
        ),
        pytest.param(
            "m/44'/1815'/2'",
            "076338cee5ab3dae19f06ccaa80e3d4428cf0e1bdc04243e41bba7be63a90da7",
            "5dcdf129f6f2d108292e615c4b67a1fc41a64e6a96130f5c981e5e8e046a6cd7",
            "",
        ),
        pytest.param(
            "m/44'/1815'/3'",
            "5f769380dc6fd17a4e0f2d23aa359442a712e5e96d7838ebb91eb020003cccc3",
            "1197ea234f528987cbac9817ebc31344395b837a3bb7c2332f87e095e70550a5",
            "",
        ),
        pytest.param(
            "m/44'/1815'/0'/0/0",
            "bc043d84b8b891d49890edb6aced6f2d78395f255c5b6aea8878b913f83e8579",
            "dc3f0d2b5cccb822335ef6213fd133f4ca934151ec44a6000aee43b8a101078c",
            "TREZOR",
            marks=with_mnemonic(MNEMONIC_SLIP39_BASIC_20_3of6),
        ),
        pytest.param(
            "m/44'/1815'/0'/0/1",
            "24c4fe188a39103db88818bc191fd8571eae7b284ebcbdf2462bde97b058a95c",
            "6f7a744035f4b3ddb8f861c18446169643cc3ae85e271b4b4f0eda05cf84c65b",
            "TREZOR",
            marks=with_mnemonic(MNEMONIC_SLIP39_BASIC_20_3of6),
        ),
        pytest.param(
            "m/44'/1815'/0'/0/2",
            "831a63d381a8dab1e6e1ee991a4300fc70687aae5f97f4fcf92ed1b6c2bd99de",
            "672d6af4707aba201b7940231e83dd357f92f8851b3dfdc224ef311e1b64cdeb",
            "TREZOR",
            marks=with_mnemonic(MNEMONIC_SLIP39_BASIC_20_3of6),
        ),
    ],
)
def test_cardano_get_public_key(client, path, public_key, chain_code, passphrase):
    client.use_passphrase(passphrase)
    key = get_public_key(client, parse_path(path))

    assert key.node.public_key.hex() == public_key
    assert key.node.chain_code.hex() == chain_code
    assert key.xpub == public_key + chain_code
