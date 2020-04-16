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

from trezorlib.cardano import (
    create_address_parameters,
    create_certificate_pointer,
    get_address,
)
from trezorlib.messages import CardanoAddressType
from trezorlib.tools import parse_path

from ..common import MNEMONIC12

SHELLEY_TEST_VECTORS_MNEMONIC = (
    "test walk nut penalty hip pave soap entry language right filter choice"
)


@pytest.mark.altcoin
@pytest.mark.cardano
@pytest.mark.skip_t1  # T1 support is not planned
@pytest.mark.parametrize(
    "path,expected_address",
    [
        (
            "m/44'/1815'/0'/0/0",
            "Ae2tdPwUPEZLCq3sFv4wVYxwqjMH2nUzBVt1HFr4v87snYrtYq3d3bq2PUQ",
        ),
        (
            "m/44'/1815'/0'/0/1",
            "Ae2tdPwUPEZEY6pVJoyuNNdLp7VbMB7U7qfebeJ7XGunk5Z2eHarkcN1bHK",
        ),
        (
            "m/44'/1815'/0'/0/2",
            "Ae2tdPwUPEZ3gZD1QeUHvAqadAV59Zid6NP9VCR9BG5LLAja9YtBUgr6ttK",
        ),
    ],
)
@pytest.mark.setup_client(mnemonic=MNEMONIC12)
def test_cardano_get_address(client, path, expected_address):
    # data from https://iancoleman.io/bip39/
    address = get_address(
        client,
        address_parameters=create_address_parameters(
            address_type=CardanoAddressType.BOOTSTRAP_ADDRESS,
            address_n=parse_path(path),
        ),
    )
    assert address == expected_address


@pytest.mark.altcoin
@pytest.mark.cardano
@pytest.mark.skip_t1  # T1 support is not planned
@pytest.mark.parametrize(
    "path, network_id, expected_address",
    [
        # data form shelley test vectors
        (
            "m/1852'/1815'/0'/0/0",
            0,
            "addr1qz2fxv2umyhttkxyxp8x0dlpdt3k6cwng5pxj3jhsydzer3jcu5d8ps7zex2k2xt3uqxgjqnnj83ws8lhrn648jjxtwqcyl47r",
        ),
        (
            "m/1852'/1815'/0'/0/0",
            3,
            "addr1qw2fxv2umyhttkxyxp8x0dlpdt3k6cwng5pxj3jhsydzer3jcu5d8ps7zex2k2xt3uqxgjqnnj83ws8lhrn648jjxtwqzhyupd",
        ),
        # data generated with code under test
        (
            "m/1852'/1815'/4'/0/0",
            0,
            "addr1qr4sh2j72ux0l03fxndjnhctdg7hcppsaejafsa84vh7lwgmcs5wgus8qt4atk45lvt4xfxpjtwfhdmvchdf2m3u3hlsuzz8x7",
        ),
        (
            "m/1852'/1815'/4'/0/0",
            3,
            "addr1q04sh2j72ux0l03fxndjnhctdg7hcppsaejafsa84vh7lwgmcs5wgus8qt4atk45lvt4xfxpjtwfhdmvchdf2m3u3hlsx3ewes",
        ),
    ],
)
@pytest.mark.setup_client(mnemonic=SHELLEY_TEST_VECTORS_MNEMONIC)
def test_cardano_get_base_address(client, path, network_id, expected_address):
    address = get_address(
        client,
        address_parameters=create_address_parameters(
            address_type=CardanoAddressType.BASE_ADDRESS, address_n=parse_path(path),
        ),
        network_id=network_id,
    )
    assert address == expected_address


@pytest.mark.altcoin
@pytest.mark.cardano
@pytest.mark.skip_t1  # T1 support is not planned
@pytest.mark.parametrize(
    "path, network_id, staking_key_hash, expected_address",
    [
        # data from shelley test vectors
        (
            "m/1852'/1815'/0'/0/0",
            0,
            "32c728d3861e164cab28cb8f006448139c8f1740ffb8e7aa9e5232dc",
            "addr1qz2fxv2umyhttkxyxp8x0dlpdt3k6cwng5pxj3jhsydzer3jcu5d8ps7zex2k2xt3uqxgjqnnj83ws8lhrn648jjxtwqcyl47r",
        ),
        (
            "m/1852'/1815'/0'/0/0",
            3,
            "32c728d3861e164cab28cb8f006448139c8f1740ffb8e7aa9e5232dc",
            "addr1qw2fxv2umyhttkxyxp8x0dlpdt3k6cwng5pxj3jhsydzer3jcu5d8ps7zex2k2xt3uqxgjqnnj83ws8lhrn648jjxtwqzhyupd",
        ),
        # data generated with code under test
        (
            "m/1852'/1815'/4'/0/0",
            0,
            "1bc428e4720702ebd5dab4fb175324c192dc9bb76cc5da956e3c8dff",
            "addr1qr4sh2j72ux0l03fxndjnhctdg7hcppsaejafsa84vh7lwgmcs5wgus8qt4atk45lvt4xfxpjtwfhdmvchdf2m3u3hlsuzz8x7",
        ),
        (
            "m/1852'/1815'/4'/0/0",
            3,
            "1bc428e4720702ebd5dab4fb175324c192dc9bb76cc5da956e3c8dff",
            "addr1q04sh2j72ux0l03fxndjnhctdg7hcppsaejafsa84vh7lwgmcs5wgus8qt4atk45lvt4xfxpjtwfhdmvchdf2m3u3hlsx3ewes",
        ),
        # staking key hash not owned - derived with "all all..." mnenomnic, data generated with code under test
        (
            "m/1852'/1815'/4'/0/0",
            0,
            "122a946b9ad3d2ddf029d3a828f0468aece76895f15c9efbd69b4277",
            "addr1qr4sh2j72ux0l03fxndjnhctdg7hcppsaejafsa84vh7lwgj922xhxkn6twlq2wn4q50q352annk3903tj00h45mgfmsh42t2h",
        ),
        (
            "m/1852'/1815'/0'/0/0",
            3,
            "122a946b9ad3d2ddf029d3a828f0468aece76895f15c9efbd69b4277",
            "addr1qw2fxv2umyhttkxyxp8x0dlpdt3k6cwng5pxj3jhsydzersj922xhxkn6twlq2wn4q50q352annk3903tj00h45mgfms3rqaac",
        ),
        (
            "m/1852'/1815'/4'/0/0",
            3,
            "122a946b9ad3d2ddf029d3a828f0468aece76895f15c9efbd69b4277",
            "addr1q04sh2j72ux0l03fxndjnhctdg7hcppsaejafsa84vh7lwgj922xhxkn6twlq2wn4q50q352annk3903tj00h45mgfmsdx3z4e",
        ),
    ],
)
@pytest.mark.setup_client(mnemonic=SHELLEY_TEST_VECTORS_MNEMONIC)
def test_cardano_get_base_address_with_staking_key_hash(
    client, path, network_id, staking_key_hash, expected_address
):
    # data form shelley test vectors
    address = get_address(
        client,
        address_parameters=create_address_parameters(
            address_type=CardanoAddressType.BASE_ADDRESS,
            address_n=parse_path(path),
            staking_key_hash=bytes.fromhex(staking_key_hash),
        ),
        network_id=network_id,
    )
    assert address == expected_address


@pytest.mark.altcoin
@pytest.mark.cardano
@pytest.mark.skip_t1  # T1 support is not planned
@pytest.mark.parametrize(
    "path, network_id, expected_address",
    [
        # data form shelley test vectors
        (
            "m/1852'/1815'/0'/0/0",
            0,
            "addr1vz2fxv2umyhttkxyxp8x0dlpdt3k6cwng5pxj3jhsydzers6g8jlq",
        ),
        (
            "m/1852'/1815'/0'/0/0",
            3,
            "addr1vw2fxv2umyhttkxyxp8x0dlpdt3k6cwng5pxj3jhsydzers6h7glf",
        ),
    ],
)
@pytest.mark.setup_client(mnemonic=SHELLEY_TEST_VECTORS_MNEMONIC)
def test_cardano_get_enterprise_address(client, path, network_id, expected_address):
    address = get_address(
        client,
        address_parameters=create_address_parameters(
            address_type=CardanoAddressType.ENTERPRISE_ADDRESS,
            address_n=parse_path(path),
        ),
        network_id=network_id,
    )
    assert address == expected_address


@pytest.mark.altcoin
@pytest.mark.cardano
@pytest.mark.skip_t1  # T1 support is not planned
@pytest.mark.parametrize(
    "path, network_id, block_index, tx_index, certificate_index, expected_address",
    [
        # data form shelley test vectors
        (
            "m/1852'/1815'/0'/0/0",
            0,
            1,
            2,
            3,
            "addr1gz2fxv2umyhttkxyxp8x0dlpdt3k6cwng5pxj3jhsydzerspqgpslhplej",
        ),
        (
            "m/1852'/1815'/0'/0/0",
            3,
            24157,
            177,
            42,
            "addr1gw2fxv2umyhttkxyxp8x0dlpdt3k6cwng5pxj3jhsydzer5ph3wczvf2x4v58t",
        ),
    ],
)
@pytest.mark.setup_client(mnemonic=SHELLEY_TEST_VECTORS_MNEMONIC)
def test_cardano_get_pointer_address(
    client, path, network_id, block_index, tx_index, certificate_index, expected_address
):
    address = get_address(
        client,
        address_parameters=create_address_parameters(
            address_type=CardanoAddressType.POINTER_ADDRESS,
            address_n=parse_path(path),
            certificate_pointer=create_certificate_pointer(
                block_index, tx_index, certificate_index
            ),
        ),
        network_id=network_id,
    )
    assert address == expected_address
