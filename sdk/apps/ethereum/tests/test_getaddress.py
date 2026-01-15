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

from trezorlib.debuglink import DebugSession as Session
from trezorlib.testing.common import parametrize_using_common_fixtures
from trezorlib.tools import parse_path

from . import ethereum_ext
from .input_flows import InputFlowShowAddressQRCode

@parametrize_using_common_fixtures("getaddress.json")
def test_getaddress(session: Session, instance_id: int, parameters, result):
    address_n = parse_path(parameters["path"])
    assert (
        ethereum_ext.get_address(session, instance_id, address_n, show_display=True)
        == result["address"]
    )


@parametrize_using_common_fixtures("getaddress.json")
def test_getaddress_chunkify_details(
    session: Session, instance_id: int, parameters, result
):
    with session.test_ctx as client:
        IF = InputFlowShowAddressQRCode(session)
        client.set_input_flow(IF.get())
        address_n = parse_path(parameters["path"])
        assert (
            ethereum_ext.get_address(
                session, instance_id, address_n, show_display=True, chunkify=True
            )
            == result["address"]
        )
