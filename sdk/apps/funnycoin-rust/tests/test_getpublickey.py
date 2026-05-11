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

from . import funnycoin
from .input_flows import InputFlowGetPublicKeyCancel
from trezorlib.debuglink import DebugSession as Session
from trezorlib.exceptions import Cancelled, TrezorFailure
from trezorlib.tools import parse_path
from trezorlib.testing.common import parametrize_using_common_fixtures


@pytest.mark.parametrize("show_display", [False, True], ids=["silent", "show_display"])
@parametrize_using_common_fixtures("getpublickey.json")
def test_ethereum_getpublickey(
    session: Session, instance_id: int, parameters, result, show_display: bool
):
    path = parse_path(parameters["path"])
    res = funnycoin.get_public_node(session, instance_id, path, show_display)
    assert res.node.depth == len(path)
    assert res.node.fingerprint == result["fingerprint"]
    assert res.node.child_num == result["child_num"]
    assert res.node.chain_code.hex() == result["chain_code"]
    assert res.node.public_key.hex() == result["public_key"]
    assert res.xpub == result["xpub"]


def test_slip25_disallowed(session: Session, instance_id: int):
    path = parse_path("m/10025'/60'/0'/0/0")
    with pytest.raises(TrezorFailure):
        funnycoin.get_public_node(session, instance_id, path)


def test_cancel_getpublickey(session: Session, instance_id: int):
    flow = InputFlowGetPublicKeyCancel(session)
    with session.test_ctx as client, pytest.raises(Cancelled):
        client.watch_layout()
        client.set_input_flow(flow.get())
        path = parse_path("m/44'/60'/0'/0/0")
        funnycoin.get_public_node(session, instance_id, path, True)
