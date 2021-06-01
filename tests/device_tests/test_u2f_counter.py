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


@pytest.mark.altcoin
def test_u2f_counter(client):
    assert fido.get_next_counter(client) == 0
    assert fido.get_next_counter(client) == 1
    fido.set_counter(client, 111111)
    assert fido.get_next_counter(client) == 111112
    assert fido.get_next_counter(client) == 111113
    fido.set_counter(client, 0)
    assert fido.get_next_counter(client) == 1
