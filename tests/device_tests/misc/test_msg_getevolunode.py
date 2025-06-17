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
from trezorlib.debuglink import SessionDebugWrapper as Session

pytestmark = [pytest.mark.altcoin, pytest.mark.models("core")]

EXPECTED_SLIP21_NODE_DATA = "a81aaf51997b6ddfa33d11c038d6aba5f711754a2c823823ff8b777825cdbb32b0e71c301fa381c75081bd3bcc134b63306aa6fc9a9f52d835ad4df8cd507be6"


def test_get_evolu_node(session: Session):
    """Test Evolu key derivation against known test vectors."""
    res = evolu.get_evolu_node(session)

    assert res.data.hex() == EXPECTED_SLIP21_NODE_DATA
