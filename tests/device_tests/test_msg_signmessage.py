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

import base64

from trezorlib import btc
from trezorlib.tools import parse_path

from .common import TrezorTest


class TestMsgSignmessage(TrezorTest):
    def test_sign(self):
        self.setup_mnemonic_nopin_nopassphrase()
        sig = btc.sign_message(
            self.client, "Bitcoin", [0], "This is an example of a signed message."
        )
        assert sig.address == "14LmW5k4ssUrtbAB4255zdqv3b4w1TuX9e"
        assert (
            sig.signature.hex()
            == "209e23edf0e4e47ff1dec27f32cd78c50e74ef018ee8a6adf35ae17c7a9b0dd96f48b493fd7dbab03efb6f439c6383c9523b3bbc5f1a7d158a6af90ab154e9be80"
        )

    def test_sign_testnet(self):
        self.setup_mnemonic_nopin_nopassphrase()
        sig = btc.sign_message(
            self.client, "Testnet", [0], "This is an example of a signed message."
        )
        assert sig.address == "mirio8q3gtv7fhdnmb3TpZ4EuafdzSs7zL"
        assert (
            sig.signature.hex()
            == "209e23edf0e4e47ff1dec27f32cd78c50e74ef018ee8a6adf35ae17c7a9b0dd96f48b493fd7dbab03efb6f439c6383c9523b3bbc5f1a7d158a6af90ab154e9be80"
        )

    def test_sign_bch(self):
        self.setup_mnemonic_nopin_nopassphrase()
        sig = btc.sign_message(
            self.client, "Bcash", [0], "This is an example of a signed message."
        )
        assert sig.address == "bitcoincash:qqj22md58nm09vpwsw82fyletkxkq36zxyxh322pru"
        assert (
            sig.signature.hex()
            == "209e23edf0e4e47ff1dec27f32cd78c50e74ef018ee8a6adf35ae17c7a9b0dd96f48b493fd7dbab03efb6f439c6383c9523b3bbc5f1a7d158a6af90ab154e9be80"
        )

    def test_sign_grs(self):
        self.setup_mnemonic_allallall()
        sig = btc.sign_message(
            self.client, "Groestlcoin", parse_path("44'/17'/0'/0/0"), "test"
        )
        assert sig.address == "Fj62rBJi8LvbmWu2jzkaUX1NFXLEqDLoZM"
        assert (
            base64.b64encode(sig.signature)
            == b"INOYaa/jj8Yxz3mD5k+bZfUmjkjB9VzoV4dNG7+RsBUyK30xL7I9yMgWWVvsL46C5yQtxtZY0cRRk7q9N6b+YTM="
        )

    def test_sign_long(self):
        self.setup_mnemonic_nopin_nopassphrase()
        sig = btc.sign_message(self.client, "Bitcoin", [0], "VeryLongMessage!" * 64)
        assert sig.address == "14LmW5k4ssUrtbAB4255zdqv3b4w1TuX9e"
        assert (
            sig.signature.hex()
            == "205ff795c29aef7538f8b3bdb2e8add0d0722ad630a140b6aefd504a5a895cbd867cbb00981afc50edd0398211e8d7c304bb8efa461181bc0afa67ea4a720a89ed"
        )

    def test_sign_utf(self):
        self.setup_mnemonic_nopin_nopassphrase()

        words_nfkd = u"Pr\u030ci\u0301s\u030cerne\u030c z\u030clut\u030couc\u030cky\u0301 ku\u030an\u030c u\u0301pe\u030cl d\u030ca\u0301belske\u0301 o\u0301dy za\u0301ker\u030cny\u0301 uc\u030cen\u030c be\u030cz\u030ci\u0301 pode\u0301l zo\u0301ny u\u0301lu\u030a"
        words_nfc = u"P\u0159\xed\u0161ern\u011b \u017elu\u0165ou\u010dk\xfd k\u016f\u0148 \xfap\u011bl \u010f\xe1belsk\xe9 \xf3dy z\xe1ke\u0159n\xfd u\u010de\u0148 b\u011b\u017e\xed pod\xe9l z\xf3ny \xfal\u016f"

        sig_nfkd = btc.sign_message(self.client, "Bitcoin", [0], words_nfkd)
        assert sig_nfkd.address == "14LmW5k4ssUrtbAB4255zdqv3b4w1TuX9e"
        assert (
            sig_nfkd.signature.hex()
            == "20d0ec02ed8da8df23e7fe9e680e7867cc290312fe1c970749d8306ddad1a1eda41c6a771b13d495dd225b13b0a9d0f915a984ee3d0703f92287bf8009fbb9f7d6"
        )

        sig_nfc = btc.sign_message(self.client, "Bitcoin", [0], words_nfc)
        assert sig_nfc.address == "14LmW5k4ssUrtbAB4255zdqv3b4w1TuX9e"
        assert (
            sig_nfc.signature.hex()
            == "20d0ec02ed8da8df23e7fe9e680e7867cc290312fe1c970749d8306ddad1a1eda41c6a771b13d495dd225b13b0a9d0f915a984ee3d0703f92287bf8009fbb9f7d6"
        )
