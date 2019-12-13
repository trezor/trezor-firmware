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

from trezorlib.elements import get_rangeproof_nonce


@pytest.mark.altcoin
@pytest.mark.elements
@pytest.mark.skip_t1  # T1 support is not planned
@pytest.mark.setup_client(mnemonic="all all all all all all all all all all all all")
def test_elements_get_rangeproof_nonce(client):
    ecdh_pubkey = bytes.fromhex(
        "02d9fd9cc80d449c276821323f46c0c5ee4a7a8aa07cc403f46b3cbf8130127b4f"
    )
    script_pubkey = bytes.fromhex("0014b31dc2a236505a6cb9201fa0411ca38a254a7bf1")
    result = get_rangeproof_nonce(
        client=client, ecdh_pubkey=ecdh_pubkey, script_pubkey=script_pubkey
    )
    expected_nonce = "db7ba9bdbf381d4c48d5971edf58bd0ea403e94313994189a5995df26369bf51"
    assert result.nonce.hex() == expected_nonce
