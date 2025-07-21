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

EXPECTED_OWNER_ID = "6edf2ed2e8d2d0eafbaae891157a57ef2856be58ce6edf9497b811c3b0b35f7d"
EXPECTED_WRITE_KEY = "748d897e4417e95f728869da7f791b9da2a4049fa3a44a27c1ccf68f43110f28"
EXPECTED_ENCRYPTION_KEY = (
    "12343fd1b7d1cf7c9e2766646c23caaadb6fa882bc38ec86da95366be45b6342"
)


def test_get_evolu_keys(client):
    """Test Evolu key derivation against known test vectors."""
    res = evolu.get_evolu_keys(client)

    assert res.owner_id.hex() == EXPECTED_OWNER_ID
    assert res.write_key.hex() == EXPECTED_WRITE_KEY
    assert res.encryption_key.hex() == EXPECTED_ENCRYPTION_KEY
