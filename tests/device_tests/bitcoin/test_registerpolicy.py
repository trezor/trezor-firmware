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

from trezorlib import btc, device, messages
from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.tools import parse_path

from ... import bip32
from ...common import is_core
from ...input_flows import InputFlowConfirmAllWarnings


def test_registerpolicy(session: Session):
    assert (
        btc.register_policy(
            session,
            "Bitcoin",
            "Basic inheritance",
            "wsh(or_d(pk(@0)...))",
            ["XPUB1", "XPUB2"],
            20,
        ).mac
        == b"\xb8\xb86\xf11\x0b\xc2\x89\xd3\xad\xef\x90\xa8.\xd2\xab\xcd\x03\xee\xf6\x1an\xdf\x06\xcd\xcd\xf9\x10\xc9\x17\xb12"
    )
