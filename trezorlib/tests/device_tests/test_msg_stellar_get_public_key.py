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
from trezorlib import stellar
from trezorlib.tools import parse_path


@pytest.mark.stellar
@pytest.mark.xfail(TREZOR_VERSION == 2, reason="T2 support is not yet finished")
class TestMsgStellarGetPublicKey(TrezorTest):

    def test_stellar_get_address(self):
        self.setup_mnemonic_nopin_nopassphrase()

        # GAK5MSF74TJW6GLM7NLTL76YZJKM2S4CGP3UH4REJHPHZ4YBZW2GSBPW
        response = self.client.stellar_get_public_key(parse_path(stellar.DEFAULT_BIP32_PATH))
        assert stellar.address_from_public_key(response.public_key) == b'GAK5MSF74TJW6GLM7NLTL76YZJKM2S4CGP3UH4REJHPHZ4YBZW2GSBPW'
