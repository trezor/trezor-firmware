# This file is part of the TREZOR project.
#
# Copyright (C) 2016-2017 Pavol Rusnak <stick@satoshilabs.com>
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

from binascii import unhexlify
import pytest

from .common import TrezorTest
from trezorlib import messages as proto


@pytest.mark.lisk
@pytest.mark.xfail  # drop when trezor-core PR #90 is merged
@pytest.mark.skip_t1
class TestMsgLiskVerifymessage(TrezorTest):

    def test_verify(self):
        self.setup_mnemonic_nopin_nopassphrase()
        with self.client:
            self.client.set_expected_responses([
                proto.ButtonRequest(code=proto.ButtonRequestType.Other),
                proto.ButtonRequest(code=proto.ButtonRequestType.Other),
                proto.Success(message='Message verified')
            ])
            self.client.lisk_verify_message(
                unhexlify('eb56d7bbb5e8ea9269405f7a8527fe126023d1db2c973cfac6f760b60ae27294'),
                unhexlify('af1d384cce25354b5af129662caed6f3514c6f1f6a206662d301fd56aa5549aa23c3f82009f213a7a4d9297015c2e5b06584273df7c42d78b4e531fe4d4fc80e'),
                'This is an example of a signed message.'
            )

    def test_verify_long(self):
        self.setup_mnemonic_nopin_nopassphrase()
        with self.client:
            self.client.set_expected_responses([
                proto.ButtonRequest(code=proto.ButtonRequestType.Other),
                proto.ButtonRequest(code=proto.ButtonRequestType.Other),
                proto.Success(message='Message verified')
            ])
            self.client.lisk_verify_message(
                unhexlify('eb56d7bbb5e8ea9269405f7a8527fe126023d1db2c973cfac6f760b60ae27294'),
                unhexlify('7b4b481f6a07a874bdd1b590cd2b933c8b571c721484d9dc303f81b22d1f3c5f55ffe0704dbfd543ff9ea3e795facda871ddb422522257d33a8fe16ab4169601'),
                'VeryLongMessage!' * 64
            )
