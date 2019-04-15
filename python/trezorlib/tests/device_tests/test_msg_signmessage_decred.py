# This file is part of the Trezor project.
#
# Copyright (C) 2012-2018 SatoshiLabs and contributors
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

from trezorlib import btc
from trezorlib.tools import parse_path

from .common import TrezorTest


@pytest.mark.decred
class TestMsgSignmessageDecred(TrezorTest):
    def test_sign_mainnet(self):
        self.setup_mnemonic_nopin_nopassphrase()
        address_n = parse_path("m/44'/42'/0'/0/0")
        sig = btc.sign_message(
            self.client, "Decred", address_n, "This is an example of a signed message."
        )
        assert sig.address == "DsbjnfJrnL1orxJBCN8Kf39NjMwEktdfdWy"
        assert (
            sig.signature.hex()
            == "20417ee6116304a65d267aec989a1450ed3699201cc0f2a6e8273a3ad31dfb3cda26a5b26f040aa3d0d76c66d6d7c1d1e5e424c1298b3ba1201c36a0a87971ed83"
        )

    def test_sign_testnet(self):
        self.setup_mnemonic_nopin_nopassphrase()
        address_n = parse_path("m/44'/1'/0'/0/0")
        sig = btc.sign_message(
            self.client,
            "Decred Testnet",
            address_n,
            "This is an example of a signed message.",
        )
        assert sig.address == "TsRQTRqf5TdEfqsnJ1gcQEDvPP363cEjr4B"
        assert (
            sig.signature.hex()
            == "20260e5665cca98e0a08ebf33346a0e1cdb7ef313d0c50d1403f5c1ea7ef5958204c9a3f3ad3fa793456365b1b3ca700c7299099646813b43dcad6249ba77a469f"
        )

    def test_sign_long(self):
        self.setup_mnemonic_nopin_nopassphrase()
        address_n = parse_path("m/44'/42'/0'/0/0")
        sig = btc.sign_message(
            self.client, "Decred", address_n, "VeryLongMessage!" * 64
        )
        assert sig.address == "DsbjnfJrnL1orxJBCN8Kf39NjMwEktdfdWy"
        assert (
            sig.signature.hex()
            == "1f4ce0f81b387d6c9ce3961baf9ae10c2fe14a2d13243ec5863131d526c77d4459636ba71217a47726ecf7517bde41e3ef95a3de10054ff88bbf8ca5cb0b5f3cea"
        )

    def test_sign_utf(self):
        self.setup_mnemonic_nopin_nopassphrase()
        address_n = parse_path("m/44'/42'/0'/0/0")

        words_nfkd = u"Pr\u030ci\u0301s\u030cerne\u030c z\u030clut\u030couc\u030cky\u0301 ku\u030an\u030c u\u0301pe\u030cl d\u030ca\u0301belske\u0301 o\u0301dy za\u0301ker\u030cny\u0301 uc\u030cen\u030c be\u030cz\u030ci\u0301 pode\u0301l zo\u0301ny u\u0301lu\u030a"
        words_nfc = u"P\u0159\xed\u0161ern\u011b \u017elu\u0165ou\u010dk\xfd k\u016f\u0148 \xfap\u011bl \u010f\xe1belsk\xe9 \xf3dy z\xe1ke\u0159n\xfd u\u010de\u0148 b\u011b\u017e\xed pod\xe9l z\xf3ny \xfal\u016f"

        sig_nfkd = btc.sign_message(self.client, "Decred", address_n, words_nfkd)
        assert sig_nfkd.address == "DsbjnfJrnL1orxJBCN8Kf39NjMwEktdfdWy"
        assert (
            sig_nfkd.signature.hex()
            == "1feb2e6eeabe6508fff655c7c3aa7b52098b09e01c9f0cfae404bd4d7baf856e762b72a4c13a8f826b7a42c0b48a5a1b12a96497ca90bd2b183e42f4b3d4eea16b"
        )

        sig_nfc = btc.sign_message(self.client, "Decred", address_n, words_nfc)
        assert sig_nfc.address == "DsbjnfJrnL1orxJBCN8Kf39NjMwEktdfdWy"
        assert (
            sig_nfc.signature.hex()
            == "1feb2e6eeabe6508fff655c7c3aa7b52098b09e01c9f0cfae404bd4d7baf856e762b72a4c13a8f826b7a42c0b48a5a1b12a96497ca90bd2b183e42f4b3d4eea16b"
        )
