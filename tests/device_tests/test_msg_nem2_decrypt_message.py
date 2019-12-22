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

import pytest
import codecs
from binascii import unhexlify

from trezorlib import nem2
from trezorlib.tools import parse_path

from ..common import MNEMONIC12

@pytest.mark.altcoin
@pytest.mark.nem2
class TestMsgNEM2GetPublicKey:

    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_nem2_decrypt_message(self, client):
        decrypted_message = nem2.decrypt_message(
            client,
            parse_path("m/44'/43'/0'/0'/0'"),
            {
                "senderPublicKey": "596FEAB15D98BFD75F1743E9DC8A36474A3D0C06AE78ED134C231336C38A6297",
                "payload": "1AFABD13380D74D58B6D50E2AA3248C3E5B73D2250E613407CA6F0C9A3E6B22D61A64CFA730FADA77FC741B9EFF5BCD447065021B09C7866CFAE5E6A88E00818"
            }
        )

        # print("MSG", decrypted_message.payload.hex())
        assert (
            decrypted_message.payload.hex().encode("utf-8")
            == "Test Transfer"
        )
