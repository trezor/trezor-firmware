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

from .common import TrezorTest
from .conftest import TREZOR_VERSION
from binascii import unhexlify, hexlify
from trezorlib import messages as proto
from trezorlib.client import CallException
import pytest


# @pytest.mark.xfail(TREZOR_VERSION == 2, reason="T2 support is not yet finished")
class TestMsgStellarVerifyMessage(TrezorTest):

    def test_stellar_verify_message(self):
        self.setup_mnemonic_nopin_nopassphrase()

        msg = 'Hello world!'
        pubkey = unhexlify('15d648bfe4d36f196cfb5735ffd8ca54cd4b8233f743f22449de7cf301cdb469')
        signature = unhexlify('3565f5885786fba6cc40c5656fe5444faec882d5e006de509c7fd6420e500179891ada79933024909cd2b57705254cd53cada422f4a7de7790e31c8c1d0c5004')
        response = self.client.stellar_verify_message(pubkey, signature, msg)
        assert response is True

        msg = 'LongMessage ' * 80  # but shorter than 1024
        pubkey = unhexlify('15d648bfe4d36f196cfb5735ffd8ca54cd4b8233f743f22449de7cf301cdb469')
        signature = unhexlify('c1e5c477b0451a1cf4b0d8328176470ad3e5aa493c65d64125af57599dfbe5ca2c5c82887aae7e3fa519bbfc3752f1f1188f48efbe4105aa91351319fcd51507')
        response = self.client.stellar_verify_message(pubkey, signature, msg)
        assert response is True

    def test_stellar_verify_message_invalid(self):
        msg = 'abc'
        pubkey = unhexlify('15d648bfe4d36f196cfb5735ffd8ca54cd4b8233f743f22449de7cf301cdb469')
        signature = unhexlify('0000000000000000')  # invalid length
        try:
            self.client.stellar_verify_message(pubkey, signature, msg)
        except CallException as exc:
            assert exc.args[0] == proto.FailureType.DataError
        else:
            assert False

        # invalid signature
        signature = unhexlify('00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000')
        try:
            self.client.stellar_verify_message(pubkey, signature, msg)
        except CallException as exc:
            assert exc.args[0] == proto.FailureType.DataError
        else:
            assert False

        # invalid pubkey
        pubkey = unhexlify('00')
        signature = unhexlify('00')
        try:
            self.client.stellar_verify_message(pubkey, signature, msg)
        except CallException as exc:
            assert exc.args[0] == proto.FailureType.DataError
        else:
            assert False
