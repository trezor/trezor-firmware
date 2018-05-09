# This file is part of the TREZOR project.
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library.  If not, see <http://www.gnu.org/licenses/>.
#
# XDR decoding tool available at:
#   https://www.stellar.org/laboratory/#xdr-viewer
#

from base64 import b64decode, b64encode
from .common import TrezorTest
from .conftest import TREZOR_VERSION
import pytest


@pytest.mark.xfail(TREZOR_VERSION == 2, reason="T2 support is not yet finished")
class TestMsgStellarSignTransaction(TrezorTest):

    def get_network_passphrase(self):
        """Use the same passphrase as the network that generated the test XDR/signatures"""
        return "Integration Test Network ; zulucrypto"

    def get_address_n(self):
        """BIP32 path of the default account"""
        return self.client.expand_path("m/44'/148'/0'")

    def test_sign_tx_bump_sequence_op(self):
        self.setup_mnemonic_nopin_nopassphrase()

        xdr = b64decode("AAAAABXWSL/k028ZbPtXNf/YylTNS4Iz90PyJEnefPMBzbRpAAAAZAAAAAEAAAAAAAAAAAAAAAAAAAABAAAAAAAAAAt//////////wAAAAAAAAAA")

        response = self.client.stellar_sign_transaction(xdr, self.get_address_n(), self.get_network_passphrase())
        assert b64encode(response.signature) == b'UAOL4ZPYIOzEgM66kBrhyNjLR66dNXtuNrmvd3m0/pc8qCSoLmYY4TybS0lHiMtb+LFZESTaxrpErMHz1sZ6DQ=='

    def test_sign_tx_account_merge_op(self):
        self.setup_mnemonic_nopin_nopassphrase()

        xdr = b64decode("AAAAABXWSL/k028ZbPtXNf/YylTNS4Iz90PyJEnefPMBzbRpAAAAZAAAAAEAAAAAAAAAAAAAAAAAAAABAAAAAAAAAAgAAAAAXVVkJGaxhbhDFS6eIZFR28WJICfsQBAaUXvtXKAwwuAAAAAAAAAAAQHNtGkAAABAgjoPRj4sW5o7NAXzYOqPK0uxfPbeKb4Qw48LJiCH/XUZ6YVCiZogePC0Z5ISUlozMh6YO6HoYtuLPbm7jq+eCA==")

        response = self.client.stellar_sign_transaction(xdr, self.get_address_n(), self.get_network_passphrase())
        assert b64encode(response.signature) == b'gjoPRj4sW5o7NAXzYOqPK0uxfPbeKb4Qw48LJiCH/XUZ6YVCiZogePC0Z5ISUlozMh6YO6HoYtuLPbm7jq+eCA=='
