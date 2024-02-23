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

from trezorlib import btc, messages, models
from trezorlib.cli import btc as btc_cli
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.tools import H_

from ...input_flows import InputFlowShowXpubQRCode

VECTORS_DESCRIPTORS = (  # coin, account, script_type, descriptors
    (
        "Bitcoin",
        0,
        44,
        messages.InputScriptType.SPENDADDRESS,
        "pkh([5c9e228d/44h/0h/0h]xpub6BiVtCpG9fQPxnPmHXG8PhtzQdWC2Su4qWu6XW9tpWFYhxydCLJGrWBJZ5H6qTAHdPQ7pQhtpjiYZVZARo14qHiay2fvrX996oEP42u8wZy/<0;1>/*)#m2cjewq5",
    ),
    (
        "Bitcoin",
        1,
        44,
        messages.InputScriptType.SPENDADDRESS,
        "pkh([5c9e228d/44h/0h/1h]xpub6BiVtCpG9fQQ1EW99bMSYwySbPWvzTFRQZCFgTmV3samLSZAYU7C3f4Je9vkNh7h1GAWi5Fn93BwoGBy9EAXbWTTgTnVKAbthHpxM1fXVRL/<0;1>/*)#rajluyqc",
    ),
    (
        "Testnet",
        0,
        44,
        messages.InputScriptType.SPENDADDRESS,
        "pkh([5c9e228d/44h/1h/0h]tpubDDKn3FtHc74CaRrRbi1WFdJNaaenZkDWqq9NsEhcafnDZ4VuKeuLG2aKHm5SuwuLgAhRkkfHqcCxpnVNSrs5kJYZXwa6Ud431VnevzzzK3U/<0;1>/*)#zye2wu3m",
    ),
    (
        "Testnet",
        1,
        44,
        messages.InputScriptType.SPENDADDRESS,
        "pkh([5c9e228d/44h/1h/1h]tpubDDKn3FtHc74CcBfxJ3zdSNnRacuggmGwv3KEZLJP2LAuqc3HhsQR5ZAVudcQzezzXs7T6QrDtoJJYvgyDUJ9vgWx3Y7Et4Ats1Q25U1LXvU/<0;1>/*)#98ps5dsf",
    ),
    (
        "Bitcoin",
        0,
        49,
        messages.InputScriptType.SPENDP2SHWITNESS,
        "sh(wpkh([5c9e228d/49h/0h/0h]xpub6CVKsQYXc9awxgV1tWbG4foDvdcnieK2JkbpPEBKB5WwAPKBZ1mstLbKVB4ov7QzxzjaxNK6EfmNY5Jsk2cG26EVcEkycGW4tchT2dyUhrx/<0;1>/*))#38fl96mv",
    ),
    (
        "Bitcoin",
        1,
        49,
        messages.InputScriptType.SPENDP2SHWITNESS,
        "sh(wpkh([5c9e228d/49h/0h/1h]xpub6CVKsQYXc9ax22ig3KAZMRiJL1xT9Me1sFX3t34mnVVzr6FkciU74qk7AqBkePQ2sM9pKeWp88KfPT2qcVQ19ykqGHMDioJhwywGuJ96Xt8/<0;1>/*))#sl78qw4y",
    ),
    (
        "Testnet",
        0,
        49,
        messages.InputScriptType.SPENDP2SHWITNESS,
        "sh(wpkh([5c9e228d/49h/1h/0h]tpubDCHRnuvE95JrpEVTUmr36sK3K9ADf3s3aztpXzL8coBeCTE8cHV8PjxS6SjWJM3GfPn798gyEa3dRPgjoUDSuNfuC9xz4PHznwKEk2XL7X1/<0;1>/*))#462xu5sy",
    ),
    (
        "Testnet",
        1,
        49,
        messages.InputScriptType.SPENDP2SHWITNESS,
        "sh(wpkh([5c9e228d/49h/1h/1h]tpubDCHRnuvE95Jrs9NkLaZwKNdoHBSoCRge6wKunXyxnspvLpx3aZbJcScTnTdsEqT6uFfWdMvBmLs3jhnkBiE7ob3xVQPV8ngDPYAMs93X9xv/<0;1>/*))#zlqkrt84",
    ),
    (
        "Bitcoin",
        0,
        84,
        messages.InputScriptType.SPENDWITNESS,
        "wpkh([5c9e228d/84h/0h/0h]xpub6DDUPHpUo4pcy43iJeZjbSVWGav1SMMmuWdMHiGtkK8rhKmfbomtkwW6GKs1GGAKehT6QRocrmda3WWxXawpjmwaUHfFRXuKrXSapdckEYF/<0;1>/*)#u9auedf8",
    ),
    (
        "Bitcoin",
        1,
        84,
        messages.InputScriptType.SPENDWITNESS,
        "wpkh([5c9e228d/84h/0h/1h]xpub6DDUPHpUo4pd1hyVtRaknvZvCgdPdEDMKx3bB5UFcx73pEHRDVK4rwEZUgeUbVuYWGMNLvuBHp5WeyPevN2Gv7m9FnLHQE6XaKNRPZcYcHH/<0;1>/*)#fdfl9z8m",
    ),
    (
        "Testnet",
        0,
        84,
        messages.InputScriptType.SPENDWITNESS,
        "wpkh([5c9e228d/84h/1h/0h]tpubDCZB6sR48s4T5Cr8qHUYSZEFCQMMHRg8AoVKVmvcAP5bRw7ArDKeoNwKAJujV3xCPkBvXH5ejSgbgyN6kREmF7sMd41NdbuHa8n1DZNxSMg/<0;1>/*)#wqdf6rm4",
    ),
    (
        "Testnet",
        1,
        84,
        messages.InputScriptType.SPENDWITNESS,
        "wpkh([5c9e228d/84h/1h/1h]tpubDCZB6sR48s4T6xoXqaYxScvf23kmQvg5QpyFkYnDBjsmviKHLSG9s6cp593Exg87tuMjXXMWDvBRXnJtzppcQf8Z8HdJP1rothfxm4qnPXo/<0;1>/*)#874stzg5",
    ),
    (
        "Bitcoin",
        0,
        86,
        messages.InputScriptType.SPENDTAPROOT,
        "tr([5c9e228d/86h/0h/0h]xpub6Bw885JisRbcKmowfBvMmCxaFHodKn1VpmRmctmJJoM8D4DzyP4qJv8ZdD9V9r3SSGjmK2KJEDnvLH6f1Q4HrobEvnCeKydNvf1eir3RHZk/<0;1>/*)#9thz2a5h",
    ),
    (
        "Bitcoin",
        1,
        86,
        messages.InputScriptType.SPENDTAPROOT,
        "tr([5c9e228d/86h/0h/1h]xpub6Bw885JisRbcLp1379q64fdNPGTnHKYGcA9wcWqGcUgkKZkYCwXSCb9Qfw8DGDgYMmcDM8QwQGooqCM3Ym4yq8kS5dBjzZSXUdVUdhyfirD/<0;1>/*)#s6l0qp0p",
    ),
    (
        "Testnet",
        0,
        86,
        messages.InputScriptType.SPENDTAPROOT,
        "tr([5c9e228d/86h/1h/0h]tpubDC88gkaZi5HvJGxGDNLADkvtdpni3mLmx6vr2KnXmWMG8zfkBRggsxHVBkUpgcwPe2KKpkyvTJCdXHb1UHEWE64vczyyPQfHr1skBcsRedN/<0;1>/*)#nyxxzyuj",
    ),
    (
        "Testnet",
        1,
        86,
        messages.InputScriptType.SPENDTAPROOT,
        "tr([5c9e228d/86h/1h/1h]tpubDC88gkaZi5HvKcrFLNkZwcXx1YyShkmPTkSNoP5MHQnSP9vTrKEYKtoeEkX4oEJmNYSm6Y3fFcNV4xbkDE1uZZBmJe1ircegxgVnBW8j4SL/<0;1>/*)#e46q5twy",
    ),
    (
        "Bitcoin",
        0,
        10025,
        messages.InputScriptType.SPENDTAPROOT,
        "tr([5c9e228d/10025h/0h/0h/1h]xpub6F9fdWTs2pmUS7phuTZbAM6XttUQoEgue5gvZToVLFcxA3jitxsbK1ZrHrGnPRJkjv9XrHW7Lqi3DnjLuv4XWXaxFdVnh6MyX4hXrkuzQgf/<0;1>/*)#lfjly5y8",
    ),
    (
        "Testnet",
        0,
        10025,
        messages.InputScriptType.SPENDTAPROOT,
        "tr([5c9e228d/10025h/1h/0h/1h]tpubDEMKm4M3S2Grx5DHTfbX9et5HQb9KhdjDCkUYdH9gvVofvPTE6yb2MH52P9uc4mx6eFohUmfN1f4hhHNK28GaZnWRXr3b8KkfFcySo1SmXU/<0;1>/*)#4frqe6n3",
    ),
)


def _address_n(purpose, coin, account, script_type):
    res = [H_(purpose), H_(0) if coin == "Bitcoin" else H_(1), H_(account)]
    if purpose == 10025 and script_type == messages.InputScriptType.SPENDTAPROOT:
        res.append(H_(1))

    return res


@pytest.mark.skip_t1
@pytest.mark.parametrize(
    "coin, account, purpose, script_type, descriptors", VECTORS_DESCRIPTORS
)
def test_descriptors(client: Client, coin, account, purpose, script_type, descriptors):
    with client:
        IF = InputFlowShowXpubQRCode(client)
        client.set_input_flow(IF.get())

        address_n = _address_n(purpose, coin, account, script_type)
        res = btc.get_public_node(
            client,
            _address_n(purpose, coin, account, script_type),
            show_display=True,
            coin_name=coin,
            script_type=script_type,
            ignore_xpub_magic=True,
            unlock_path=btc_cli.get_unlock_path(address_n),
        )
        assert res.descriptor == descriptors


@pytest.mark.parametrize(
    "coin, account, purpose, script_type, descriptors", VECTORS_DESCRIPTORS
)
def test_descriptors_trezorlib(
    client: Client, coin, account, purpose, script_type, descriptors
):
    with client:
        if client.model != models.T1B1:
            IF = InputFlowShowXpubQRCode(client)
            client.set_input_flow(IF.get())
        res = btc_cli._get_descriptor(
            client, coin, account, purpose, script_type, show_display=True
        )
        assert res == descriptors
