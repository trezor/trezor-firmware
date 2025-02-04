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

from trezorlib import messages
from trezorlib.debuglink import SessionDebugWrapper as Session


def test_ping(session: Session):
    with session:
        session.set_expected_responses([messages.Success])
        res = session.call(messages.Ping(message="random data"))
        assert res.message == "random data"

    with session:
        session.set_expected_responses(
            [
                messages.ButtonRequest(code=messages.ButtonRequestType.ProtectCall),
                messages.Success,
            ]
        )
        res = session.call(
            messages.Ping(message="random data 2", button_protection=True)
        )
        assert res.message == "random data 2"
