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

from trezorlib import ethereum_ext
from trezorlib.debuglink import DebugSession as Session
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import parse_path

from ...common import parametrize_using_common_fixtures

pytestmark = [pytest.mark.extapp]


@parametrize_using_common_fixtures("ethereum/getpublickey.json")
def test_ethereum_getpublickey(session: Session, instance_id: int, parameters, result):
    path = parse_path(parameters["path"])
    res = ethereum_ext.get_public_node(session, instance_id, path)
    assert res.node.depth == len(path)
    assert res.node.fingerprint == result["fingerprint"]
    assert res.node.child_num == result["child_num"]
    assert res.node.chain_code.hex() == result["chain_code"]
    assert res.node.public_key.hex() == result["public_key"]
    assert res.xpub == result["xpub"]


def test_slip25_disallowed(session: Session, instance_id: int):
    path = parse_path("m/10025'/60'/0'/0/0")
    with pytest.raises(TrezorFailure):
        ethereum_ext.get_public_node(session, instance_id, path)
