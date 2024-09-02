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

from trezorlib import device, exceptions
from trezorlib.debuglink import TrezorClientDebugLink as Client

from ..input_flows import InputFlowTutorial


# TODO not initialized?
@pytest.mark.setup_client(uninitialized=True)
@pytest.mark.models("safe")
def test_tutorial(client: Client):
    with client:
        IF = InputFlowTutorial(client, cancel=False)
        client.set_input_flow(IF.get())
        device.show_device_tutorial(client)

    assert client.features.initialized is False


@pytest.mark.setup_client(uninitialized=True)
@pytest.mark.models("safe")
def test_tutorial_cancel(client: Client):
    with client:
        IF = InputFlowTutorial(client, cancel=True)
        client.set_input_flow(IF.get())
        with pytest.raises(exceptions.Cancelled):
            device.show_device_tutorial(client)

    assert client.features.initialized is False
