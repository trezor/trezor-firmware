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

from trezorlib import btc
from trezorlib.debuglink import TrezorClientDebugLink as Client


def test_message_long(client: Client):
    ret = btc.verify_message(
        client,
        "Bitcoin",
        "3CwYaeWxhpXXiHue3ciQez1DLaTEAXcKa1",
        bytes.fromhex(
            "245ff795c29aef7538f8b3bdb2e8add0d0722ad630a140b6aefd504a5a895cbd867cbb00981afc50edd0398211e8d7c304bb8efa461181bc0afa67ea4a720a89ed"
        ),
        "VeryLongMessage!" * 64,
    )
    assert ret is True


def test_message_testnet(client: Client):
    ret = btc.verify_message(
        client,
        "Testnet",
        "2N4VkePSzKH2sv5YBikLHGvzUYvfPxV6zS9",
        bytes.fromhex(
            "249e23edf0e4e47ff1dec27f32cd78c50e74ef018ee8a6adf35ae17c7a9b0dd96f48b493fd7dbab03efb6f439c6383c9523b3bbc5f1a7d158a6af90ab154e9be80"
        ),
        "This is an example of a signed message.",
    )
    assert ret is True


def test_message_verify(client: Client):
    res = btc.verify_message(
        client,
        "Bitcoin",
        "3CwYaeWxhpXXiHue3ciQez1DLaTEAXcKa1",
        bytes.fromhex(
            "249e23edf0e4e47ff1dec27f32cd78c50e74ef018ee8a6adf35ae17c7a9b0dd96f48b493fd7dbab03efb6f439c6383c9523b3bbc5f1a7d158a6af90ab154e9be80"
        ),
        "This is an example of a signed message.",
    )
    assert res is True

    # no script type
    res = btc.verify_message(
        client,
        "Bitcoin",
        "3L6TyTisPBmrDAj6RoKmDzNnj4eQi54gD2",
        bytes.fromhex(
            "1f744de4516fac5c140808015664516a32fead94de89775cec7e24dbc24fe133075ac09301c4cc8e197bea4b6481661d5b8e9bf19d8b7b8a382ecdb53c2ee0750d"
        ),
        "This is an example of a signed message.",
    )
    assert res is True

    # trezor pubkey - FAIL - wrong sig
    res = btc.verify_message(
        client,
        "Bitcoin",
        "3CwYaeWxhpXXiHue3ciQez1DLaTEAXcKa1",
        bytes.fromhex(
            "249e23edf0e4e47ff1dec27f32cd78c50e74ef018ee8a6adf35ae17c7a9b0dd96f48b493fd7dbab03efb6f439c6383c9523b3bbc5f1a7d158a6af90ab154e9be00"
        ),
        "This is an example of a signed message.",
    )
    assert res is False

    # trezor pubkey - FAIL - wrong msg
    res = btc.verify_message(
        client,
        "Bitcoin",
        "3CwYaeWxhpXXiHue3ciQez1DLaTEAXcKa1",
        bytes.fromhex(
            "249e23edf0e4e47ff1dec27f32cd78c50e74ef018ee8a6adf35ae17c7a9b0dd96f48b493fd7dbab03efb6f439c6383c9523b3bbc5f1a7d158a6af90ab154e9be80"
        ),
        "This is an example of a signed message!",
    )
    assert res is False


def test_verify_utf(client: Client):
    words_nfkd = "Pr\u030ci\u0301s\u030cerne\u030c z\u030clut\u030couc\u030cky\u0301 ku\u030an\u030c u\u0301pe\u030cl d\u030ca\u0301belske\u0301 o\u0301dy za\u0301ker\u030cny\u0301 uc\u030cen\u030c be\u030cz\u030ci\u0301 pode\u0301l zo\u0301ny u\u0301lu\u030a"
    words_nfc = "P\u0159\xed\u0161ern\u011b \u017elu\u0165ou\u010dk\xfd k\u016f\u0148 \xfap\u011bl \u010f\xe1belsk\xe9 \xf3dy z\xe1ke\u0159n\xfd u\u010de\u0148 b\u011b\u017e\xed pod\xe9l z\xf3ny \xfal\u016f"

    res_nfkd = btc.verify_message(
        client,
        "Bitcoin",
        "3CwYaeWxhpXXiHue3ciQez1DLaTEAXcKa1",
        bytes.fromhex(
            "24d0ec02ed8da8df23e7fe9e680e7867cc290312fe1c970749d8306ddad1a1eda41c6a771b13d495dd225b13b0a9d0f915a984ee3d0703f92287bf8009fbb9f7d6"
        ),
        words_nfkd,
    )

    res_nfc = btc.verify_message(
        client,
        "Bitcoin",
        "3CwYaeWxhpXXiHue3ciQez1DLaTEAXcKa1",
        bytes.fromhex(
            "24d0ec02ed8da8df23e7fe9e680e7867cc290312fe1c970749d8306ddad1a1eda41c6a771b13d495dd225b13b0a9d0f915a984ee3d0703f92287bf8009fbb9f7d6"
        ),
        words_nfc,
    )

    assert res_nfkd is True
    assert res_nfc is True
