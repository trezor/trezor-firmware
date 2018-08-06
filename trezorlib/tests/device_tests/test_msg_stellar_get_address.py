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
class TestMsgStellarGetAddress(TrezorTest):

    def test_stellar_get_address(self):
        self.setup_mnemonic_nopin_nopassphrase()

        address = self.client.stellar_get_address(parse_path(stellar.DEFAULT_BIP32_PATH))
        assert address == 'GAK5MSF74TJW6GLM7NLTL76YZJKM2S4CGP3UH4REJHPHZ4YBZW2GSBPW'

    def test_stellar_get_address_sep(self):
        # data from https://github.com/stellar/stellar-protocol/blob/master/ecosystem/sep-0005.md
        self.client.load_device_by_mnemonic(
            mnemonic='illness spike retreat truth genius clock brain pass fit cave bargain toe',
            pin='',
            passphrase_protection=False,
            label='test',
            language='english')

        address = self.client.stellar_get_address(parse_path(stellar.DEFAULT_BIP32_PATH))
        assert address == 'GDRXE2BQUC3AZNPVFSCEZ76NJ3WWL25FYFK6RGZGIEKWE4SOOHSUJUJ6'

        address = self.client.stellar_get_address(parse_path("m/44h/148h/1h"), show_display=True)
        assert address == 'GBAW5XGWORWVFE2XTJYDTLDHXTY2Q2MO73HYCGB3XMFMQ562Q2W2GJQX'

    def test_stellar_get_address_get_pubkey(self):
        self.setup_mnemonic_nopin_nopassphrase()

        pubkey = self.client.stellar_get_public_key(parse_path(stellar.DEFAULT_BIP32_PATH))
        # GAK5MSF74TJW6GLM7NLTL76YZJKM2S4CGP3UH4REJHPHZ4YBZW2GSBPW
        address = self.client.stellar_get_address(parse_path(stellar.DEFAULT_BIP32_PATH))

        assert stellar.address_from_public_key(pubkey) == address

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
