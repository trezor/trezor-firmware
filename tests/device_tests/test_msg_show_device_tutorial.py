# This file is part of the Trezor project.
#
# Copyright (C) 2012-2024 SatoshiLabs and contributors
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

from trezorlib import device
from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.exceptions import Cancelled


@pytest.mark.setup_client(uninitialized=True)
@pytest.mark.uninitialized_session
@pytest.mark.models("safe", skip=["eckhart"])
def test_tutorial(session: Session):
    device.show_device_tutorial(session)
    assert session.features.initialized is False


@pytest.mark.setup_client(uninitialized=True)
@pytest.mark.uninitialized_session
def test_tutorial_cancel(session: Session):

    session.ping(message="before")

    def input_flow():
        yield
        session.cancel()

    with pytest.raises(Cancelled), session.client as client:
        client.set_input_flow(input_flow)
        device.show_device_tutorial(session)

    session.ping(message="after")
