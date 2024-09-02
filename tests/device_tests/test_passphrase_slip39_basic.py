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

from trezorlib.debuglink import TrezorClientDebugLink as Client

from ..common import (
    MNEMONIC_SLIP39_BASIC_20_3of6,
    MNEMONIC_SLIP39_BASIC_EXT_20_2of3,
    get_test_address,
)

pytestmark = pytest.mark.models("core")


@pytest.mark.setup_client(mnemonic=MNEMONIC_SLIP39_BASIC_20_3of6, passphrase="TREZOR")
def test_3of6_passphrase(client: Client):
    """
    BIP32 Root Key for passphrase TREZOR:
    provided by Andrew, address calculated via https://iancoleman.io/bip39/
    xprv9s21ZrQH143K2pMWi8jrTawHaj16uKk4CSbvo4Zt61tcrmuUDMx2o1Byzcr3saXNGNvHP8zZgXVdJHsXVdzYFPavxvCyaGyGr1WkAYG83ce
    """
    assert client.features.passphrase_protection is True
    address = get_test_address(client)
    assert address == "mi4HXfRJAqCDyEdet5veunBvXLTKSxpuim"


@pytest.mark.setup_client(
    mnemonic=(
        "hobo romp academic axis august founder knife legal recover alien expect emphasis loan kitchen involve teacher capture rebuild trial numb spider forward ladle lying voter typical security quantity hawk legs idle leaves gasoline",
        "hobo romp academic agency ancestor industry argue sister scene midst graduate profile numb paid headset airport daisy flame express scene usual welcome quick silent downtown oral critical step remove says rhythm venture aunt",
    ),
    passphrase="TREZOR",
)
def test_2of5_passphrase(client: Client):
    """
    BIP32 Root Key for passphrase TREZOR:
    provided by Andrew, address calculated via https://iancoleman.io/bip39/
    xprv9s21ZrQH143K2o6EXEHpVy8TCYoMmkBnDCCESLdR2ieKwmcNG48ck2XJQY4waS7RUQcXqR9N7HnQbUVEDMWYyREdF1idQqxFHuCfK7fqFni
    """
    assert client.features.passphrase_protection is True
    address = get_test_address(client)
    assert address == "mjXH4pN7TtbHp3tWLqVKktKuaQeByHMoBZ"


@pytest.mark.setup_client(
    mnemonic=MNEMONIC_SLIP39_BASIC_EXT_20_2of3, passphrase="TREZOR"
)
def test_2of3_ext_passphrase(client: Client):
    """
    BIP32 Root Key for passphrase TREZOR:
    xprv9s21ZrQH143K4FS1qQdXYAFVAHiSAnjj21YAKGh2CqUPJ2yQhMmYGT4e5a2tyGLiVsRgTEvajXkxhg92zJ8zmWZas9LguQWz7WZShfJg6RS
    """
    assert client.features.passphrase_protection is True
    address = get_test_address(client)
    assert address == "moELJhDbGK41k6J2ePYh2U8uc5qskC663C"
