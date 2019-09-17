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

from trezorlib import btc, debuglink, device
from trezorlib.messages.PassphraseSourceType import HOST as PASSPHRASE_ON_HOST

from ..common import MNEMONIC_SLIP39_ADVANCED_20, MNEMONIC_SLIP39_ADVANCED_33


@pytest.mark.setup_client(mnemonic=MNEMONIC_SLIP39_ADVANCED_20, passphrase=True)
@pytest.mark.skip_t1
def test_128bit_passphrase(client):
    """
    BIP32 Root Key for passphrase TREZOR:
    provided by Andrew, address calculated using Model T
    xprv9s21ZrQH143K3dzDLfeY3cMp23u5vDeFYftu5RPYZPucKc99mNEddU4w99GxdgUGcSfMpVDxhnR1XpJzZNXRN1m6xNgnzFS5MwMP6QyBRKV
    """
    assert client.features.passphrase_protection is True
    client.set_passphrase("TREZOR")
    address = btc.get_address(client, "Bitcoin", [])
    assert address == "1CX5rv2vbSV8YFAZEAdMwRVqbxxswPnSPw"
    device.wipe(client)
    debuglink.load_device_by_mnemonic(
        client,
        mnemonic=MNEMONIC_SLIP39_ADVANCED_20,
        pin="",
        passphrase_protection=True,
        label="test",
        language="english",
        skip_checksum=True,
    )
    if client.features.model == "T":
        device.apply_settings(client, passphrase_source=PASSPHRASE_ON_HOST)
    client.set_passphrase("ROZERT")
    address_compare = btc.get_address(client, "Bitcoin", [])
    assert address != address_compare


@pytest.mark.setup_client(mnemonic=MNEMONIC_SLIP39_ADVANCED_33, passphrase=True)
@pytest.mark.skip_t1
def test_256bit_passphrase(client):
    """
    BIP32 Root Key for passphrase TREZOR:
    provided by Andrew, address calculated using Model T
    xprv9s21ZrQH143K2UspC9FRPfQC9NcDB4HPkx1XG9UEtuceYtpcCZ6ypNZWdgfxQ9dAFVeD1F4Zg4roY7nZm2LB7THPD6kaCege3M7EuS8v85c
    """
    assert client.features.passphrase_protection is True
    client.set_passphrase("TREZOR")
    address = btc.get_address(client, "Bitcoin", [])
    assert address == "18oNx6UczHWASBQXc5XQqdSdAAZyhUwdQU"
    device.wipe(client)
    debuglink.load_device_by_mnemonic(
        client,
        mnemonic=MNEMONIC_SLIP39_ADVANCED_33,
        pin="",
        passphrase_protection=True,
        label="test",
        language="english",
        skip_checksum=True,
    )
    if client.features.model == "T":
        device.apply_settings(client, passphrase_source=PASSPHRASE_ON_HOST)
    client.set_passphrase("ROZERT")
    address_compare = btc.get_address(client, "Bitcoin", [])
    assert address != address_compare
