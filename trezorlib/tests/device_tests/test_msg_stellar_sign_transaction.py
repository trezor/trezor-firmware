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

from base64 import b64encode
from .common import TrezorTest
from .conftest import TREZOR_VERSION
from binascii import hexlify, unhexlify
from trezorlib import messages as proto
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

        op = proto.StellarBumpSequenceOp()
        op.bump_to = 0x7fffffffffffffff
        tx = self._create_msg()

        response = self.client.stellar_sign_transaction(tx, [op], self.get_address_n(), self.get_network_passphrase())
        assert b64encode(response.signature) == b'UAOL4ZPYIOzEgM66kBrhyNjLR66dNXtuNrmvd3m0/pc8qCSoLmYY4TybS0lHiMtb+LFZESTaxrpErMHz1sZ6DQ=='

    def test_sign_tx_account_merge_op(self):
        self.setup_mnemonic_nopin_nopassphrase()

        op = proto.StellarAccountMergeOp()
        op.destination_account = unhexlify('5d55642466b185b843152e9e219151dbc5892027ec40101a517bed5ca030c2e0')

        tx = self._create_msg()

        response = self.client.stellar_sign_transaction(tx, [op], self.get_address_n(), self.get_network_passphrase())
        assert b64encode(response.signature) == b'gjoPRj4sW5o7NAXzYOqPK0uxfPbeKb4Qw48LJiCH/XUZ6YVCiZogePC0Z5ISUlozMh6YO6HoYtuLPbm7jq+eCA=='

    def _create_msg(self) -> proto.StellarSignTx:
        tx = proto.StellarSignTx()
        tx.protocol_version = 1
        tx.source_account = unhexlify('15d648bfe4d36f196cfb5735ffd8ca54cd4b8233f743f22449de7cf301cdb469')
        tx.fee = 100
        tx.sequence_number = 0x100000000
        tx.memo_type = 0
        return tx
