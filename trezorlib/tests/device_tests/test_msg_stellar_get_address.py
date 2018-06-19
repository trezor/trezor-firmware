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
import pytest

from .common import TrezorTest
from .conftest import TREZOR_VERSION
from binascii import hexlify
from trezorlib import stellar
from trezorlib import messages as proto
from trezorlib.client import CallException
from trezorlib.tools import parse_path


@pytest.mark.stellar
@pytest.mark.xfail(TREZOR_VERSION == 1, reason="T1 support is not yet finished")
@pytest.mark.xfail(TREZOR_VERSION == 2, reason="T2 support is not yet finished")
class TestMsgStellarGetAddress(TrezorTest):

    def test_stellar_get_address(self):
        self.setup_mnemonic_nopin_nopassphrase()

        # GAK5MSF74TJW6GLM7NLTL76YZJKM2S4CGP3UH4REJHPHZ4YBZW2GSBPW
        address = self.client.stellar_get_address(parse_path(stellar.DEFAULT_BIP32_PATH))
        assert address == 'GAK5MSF74TJW6GLM7NLTL76YZJKM2S4CGP3UH4REJHPHZ4YBZW2GSBPW'

    def test_stellar_get_address_get_pubkey(self):
        self.setup_mnemonic_nopin_nopassphrase()

        pubkey = self.client.stellar_get_public_key(parse_path(stellar.DEFAULT_BIP32_PATH))
        # GAK5MSF74TJW6GLM7NLTL76YZJKM2S4CGP3UH4REJHPHZ4YBZW2GSBPW
        address = self.client.stellar_get_address(parse_path(stellar.DEFAULT_BIP32_PATH))

        assert stellar.address_from_public_key(pubkey).decode('utf8') == address

    def test_stellar_get_address_fail(self):
        self.setup_mnemonic_nopin_nopassphrase()

        with pytest.raises(CallException) as exc:
            self.client.stellar_get_address(parse_path('m/0/1'))

        if TREZOR_VERSION == 1:
            assert exc.value.args[0] == proto.FailureType.ProcessError
            assert exc.value.args[1].endswith('Failed to derive private key')
        else:
            assert exc.value.args[0] == proto.FailureType.FirmwareError
            assert exc.value.args[1].endswith('Firmware error')
