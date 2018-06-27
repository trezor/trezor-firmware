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

from .common import TrezorTest
from .conftest import TREZOR_VERSION
from binascii import hexlify
from trezorlib import stellar
from trezorlib import messages as proto
from trezorlib.client import CallException
from trezorlib.tools import parse_path


@pytest.mark.stellar
@pytest.mark.xfail(TREZOR_VERSION == 2, reason="T2 support is not yet finished")
class TestMsgStellarGetPublicKey(TrezorTest):

    def test_stellar_get_public_key(self):
        self.setup_mnemonic_nopin_nopassphrase()

        # GAK5MSF74TJW6GLM7NLTL76YZJKM2S4CGP3UH4REJHPHZ4YBZW2GSBPW
        response = self.client.stellar_get_public_key(parse_path(stellar.DEFAULT_BIP32_PATH))
        assert hexlify(response) == b'15d648bfe4d36f196cfb5735ffd8ca54cd4b8233f743f22449de7cf301cdb469'
        assert stellar.address_from_public_key(response) == b'GAK5MSF74TJW6GLM7NLTL76YZJKM2S4CGP3UH4REJHPHZ4YBZW2GSBPW'

    def test_stellar_get_public_key_fail(self):
        self.setup_mnemonic_nopin_nopassphrase()

        with pytest.raises(CallException) as exc:
            self.client.stellar_get_public_key(parse_path('m/0/1'))

        if TREZOR_VERSION == 1:
            assert exc.value.args[0] == proto.FailureType.ProcessError
            assert exc.value.args[1].endswith('Failed to derive private key')
        else:
            assert exc.value.args[0] == proto.FailureType.FirmwareError
            assert exc.value.args[1].endswith('Firmware error')
