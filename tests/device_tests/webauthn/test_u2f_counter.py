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

from trezorlib import fido
from trezorlib.debuglink import SessionDebugWrapper as Session


@pytest.mark.altcoin
@pytest.mark.models(skip=["eckhart"])
def test_u2f_counter(session: Session):
    assert fido.get_next_counter(session) == 0
    assert fido.get_next_counter(session) == 1
    fido.set_counter(session, 111111)
    assert fido.get_next_counter(session) == 111112
    assert fido.get_next_counter(session) == 111113
    fido.set_counter(session, 0)
    assert fido.get_next_counter(session) == 1
