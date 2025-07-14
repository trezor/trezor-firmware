# This file is part of the Trezor project.
#
# Copyright (C) 2012-2025 SatoshiLabs and contributors
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

from trezorlib import evolu

pytestmark = [pytest.mark.altcoin, pytest.mark.models("core")]

ALL_MNEMONIC = "all all all all all all all all all all all all"

EXPECTED_OWNER_ID = "0940d9f3e307f3bcedbcc8361ae136b619603a686386ecd329c3ed2337cb831d"
EXPECTED_WRITE_KEY = "2a65e7495bc4edc8ad365c5278404467fc2ec1b3e6978e2406f59329d5357f3e"
EXPECTED_ENCRYPTION_KEY = (
    "9ad06a43e9d4739502d59c8cafdaa6babb0481cdd0b3acb8455f080b38847642"
)

pytestmark_all_mnemonic = pytest.mark.setup_client(mnemonic=ALL_MNEMONIC)


@pytestmark_all_mnemonic
def test_get_evolu_keys(client):
    """Test Evolu key derivation against known test vectors."""
    response = evolu.get_evolu_keys(client)

    assert response.owner_id.hex() == EXPECTED_OWNER_ID
    assert response.write_key.hex() == EXPECTED_WRITE_KEY
    assert response.encryption_key.hex() == EXPECTED_ENCRYPTION_KEY
