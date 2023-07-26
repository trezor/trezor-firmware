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
from trezorlib.cli import btc
from trezorlib.debuglink import TrezorClientDebugLink as Client

from ...input_flows import InputFlowShowXpubQRCode

VECTORS_DESCRIPTORS = (  # coin, account, script_type, descriptors
    (
        "Bitcoin",
        0,
        44,
        messages.InputScriptType.SPENDADDRESS,
        "pkh([5c9e228d/44'/0'/0']xpub6BiVtCpG9fQPxnPmHXG8PhtzQdWC2Su4qWu6XW9tpWFYhxydCLJGrWBJZ5H6qTAHdPQ7pQhtpjiYZVZARo14qHiay2fvrX996oEP42u8wZy/<0;1>/*)#t3pfpx6p",
    ),
    (
        "Bitcoin",
        1,
        44,
        messages.InputScriptType.SPENDADDRESS,
        "pkh([5c9e228d/44'/0'/1']xpub6BiVtCpG9fQQ1EW99bMSYwySbPWvzTFRQZCFgTmV3samLSZAYU7C3f4Je9vkNh7h1GAWi5Fn93BwoGBy9EAXbWTTgTnVKAbthHpxM1fXVRL/<0;1>/*)#nxtyyv6d",
    ),
    (
        "Testnet",
        0,
        44,
        messages.InputScriptType.SPENDADDRESS,
        "pkh([5c9e228d/44'/1'/0']tpubDDKn3FtHc74CaRrRbi1WFdJNaaenZkDWqq9NsEhcafnDZ4VuKeuLG2aKHm5SuwuLgAhRkkfHqcCxpnVNSrs5kJYZXwa6Ud431VnevzzzK3U/<0;1>/*)#jlq3k5tw",
    ),
    (
        "Testnet",
        1,
        44,
        messages.InputScriptType.SPENDADDRESS,
        "pkh([5c9e228d/44'/1'/1']tpubDDKn3FtHc74CcBfxJ3zdSNnRacuggmGwv3KEZLJP2LAuqc3HhsQR5ZAVudcQzezzXs7T6QrDtoJJYvgyDUJ9vgWx3Y7Et4Ats1Q25U1LXvU/<0;1>/*)#4uctv92u",
    ),
    (
        "Bitcoin",
        0,
        49,
        messages.InputScriptType.SPENDP2SHWITNESS,
        "sh(wpkh([5c9e228d/49'/0'/0']xpub6CVKsQYXc9awxgV1tWbG4foDvdcnieK2JkbpPEBKB5WwAPKBZ1mstLbKVB4ov7QzxzjaxNK6EfmNY5Jsk2cG26EVcEkycGW4tchT2dyUhrx/<0;1>/*))#a49xle58",
    ),
    (
        "Bitcoin",
        1,
        49,
        messages.InputScriptType.SPENDP2SHWITNESS,
        "sh(wpkh([5c9e228d/49'/0'/1']xpub6CVKsQYXc9ax22ig3KAZMRiJL1xT9Me1sFX3t34mnVVzr6FkciU74qk7AqBkePQ2sM9pKeWp88KfPT2qcVQ19ykqGHMDioJhwywGuJ96Xt8/<0;1>/*))#udj76d60",
    ),
    (
        "Testnet",
        0,
        49,
        messages.InputScriptType.SPENDP2SHWITNESS,
        "sh(wpkh([5c9e228d/49'/1'/0']tpubDCHRnuvE95JrpEVTUmr36sK3K9ADf3s3aztpXzL8coBeCTE8cHV8PjxS6SjWJM3GfPn798gyEa3dRPgjoUDSuNfuC9xz4PHznwKEk2XL7X1/<0;1>/*))#egxlxhl0",
    ),
    (
        "Testnet",
        1,
        49,
        messages.InputScriptType.SPENDP2SHWITNESS,
        "sh(wpkh([5c9e228d/49'/1'/1']tpubDCHRnuvE95Jrs9NkLaZwKNdoHBSoCRge6wKunXyxnspvLpx3aZbJcScTnTdsEqT6uFfWdMvBmLs3jhnkBiE7ob3xVQPV8ngDPYAMs93X9xv/<0;1>/*))#wdv0egg7",
    ),
    (
        "Bitcoin",
        0,
        84,
        messages.InputScriptType.SPENDWITNESS,
        "wpkh([5c9e228d/84'/0'/0']xpub6DDUPHpUo4pcy43iJeZjbSVWGav1SMMmuWdMHiGtkK8rhKmfbomtkwW6GKs1GGAKehT6QRocrmda3WWxXawpjmwaUHfFRXuKrXSapdckEYF/<0;1>/*)#tdqj4vr6",
    ),
    (
        "Bitcoin",
        1,
        84,
        messages.InputScriptType.SPENDWITNESS,
        "wpkh([5c9e228d/84'/0'/1']xpub6DDUPHpUo4pd1hyVtRaknvZvCgdPdEDMKx3bB5UFcx73pEHRDVK4rwEZUgeUbVuYWGMNLvuBHp5WeyPevN2Gv7m9FnLHQE6XaKNRPZcYcHH/<0;1>/*)#7953frdx",
    ),
    (
        "Testnet",
        0,
        84,
        messages.InputScriptType.SPENDWITNESS,
        "wpkh([5c9e228d/84'/1'/0']tpubDCZB6sR48s4T5Cr8qHUYSZEFCQMMHRg8AoVKVmvcAP5bRw7ArDKeoNwKAJujV3xCPkBvXH5ejSgbgyN6kREmF7sMd41NdbuHa8n1DZNxSMg/<0;1>/*)#egs8kz3g",
    ),
    (
        "Testnet",
        1,
        84,
        messages.InputScriptType.SPENDWITNESS,
        "wpkh([5c9e228d/84'/1'/1']tpubDCZB6sR48s4T6xoXqaYxScvf23kmQvg5QpyFkYnDBjsmviKHLSG9s6cp593Exg87tuMjXXMWDvBRXnJtzppcQf8Z8HdJP1rothfxm4qnPXo/<0;1>/*)#skg78rzf",
    ),
    (
        "Bitcoin",
        0,
        86,
        messages.InputScriptType.SPENDTAPROOT,
        "tr([5c9e228d/86'/0'/0']xpub6Bw885JisRbcKmowfBvMmCxaFHodKn1VpmRmctmJJoM8D4DzyP4qJv8ZdD9V9r3SSGjmK2KJEDnvLH6f1Q4HrobEvnCeKydNvf1eir3RHZk/<0;1>/*)#4swej4wz",
    ),
    (
        "Bitcoin",
        1,
        86,
        messages.InputScriptType.SPENDTAPROOT,
        "tr([5c9e228d/86'/0'/1']xpub6Bw885JisRbcLp1379q64fdNPGTnHKYGcA9wcWqGcUgkKZkYCwXSCb9Qfw8DGDgYMmcDM8QwQGooqCM3Ym4yq8kS5dBjzZSXUdVUdhyfirD/<0;1>/*)#qpx5cf45",
    ),
    (
        "Testnet",
        0,
        86,
        messages.InputScriptType.SPENDTAPROOT,
        "tr([5c9e228d/86'/1'/0']tpubDC88gkaZi5HvJGxGDNLADkvtdpni3mLmx6vr2KnXmWMG8zfkBRggsxHVBkUpgcwPe2KKpkyvTJCdXHb1UHEWE64vczyyPQfHr1skBcsRedN/<0;1>/*)#rlla6vx8",
    ),
    (
        "Testnet",
        1,
        86,
        messages.InputScriptType.SPENDTAPROOT,
        "tr([5c9e228d/86'/1'/1']tpubDC88gkaZi5HvKcrFLNkZwcXx1YyShkmPTkSNoP5MHQnSP9vTrKEYKtoeEkX4oEJmNYSm6Y3fFcNV4xbkDE1uZZBmJe1ircegxgVnBW8j4SL/<0;1>/*)#fwrmvr53",
    ),
    (
        "Bitcoin",
        0,
        10025,
        messages.InputScriptType.SPENDTAPROOT,
        "tr([5c9e228d/10025'/0'/0'/1']xpub6F9fdWTs2pmUS7phuTZbAM6XttUQoEgue5gvZToVLFcxA3jitxsbK1ZrHrGnPRJkjv9XrHW7Lqi3DnjLuv4XWXaxFdVnh6MyX4hXrkuzQgf/<0;1>/*)#llpu5z9x",
    ),
    (
        "Testnet",
        0,
        10025,
        messages.InputScriptType.SPENDTAPROOT,
        "tr([5c9e228d/10025'/1'/0'/1']tpubDEMKm4M3S2Grx5DHTfbX9et5HQb9KhdjDCkUYdH9gvVofvPTE6yb2MH52P9uc4mx6eFohUmfN1f4hhHNK28GaZnWRXr3b8KkfFcySo1SmXU/<0;1>/*)#4lsrfvjs",
    ),
)


@pytest.mark.parametrize(
    "coin, account, purpose, script_type, descriptors", VECTORS_DESCRIPTORS
)
def test_descriptors(client: Client, coin, account, purpose, script_type, descriptors):
    with client:
        if client.features.model != "1":
            IF = InputFlowShowXpubQRCode(client)
            client.set_input_flow(IF.get())
        res = btc._get_descriptor(
            client, coin, account, purpose, script_type, show_display=True
        )
        assert res == descriptors
