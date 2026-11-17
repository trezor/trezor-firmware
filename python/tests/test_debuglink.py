# This file is part of the Trezor project.
#
# Copyright (C) SatoshiLabs and contributors
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

from __future__ import annotations

from types import SimpleNamespace

import pytest

from trezorlib import messages
from trezorlib.debuglink import TrezorTestContext


def make_ctx() -> TrezorTestContext:
    # no device: only the state that `reset_debug_features` and `__exit__` touch
    ctx = TrezorTestContext.__new__(TrezorTestContext)
    ctx.debug = SimpleNamespace(input_wait_type=None)  # type: ignore [assignment]
    ctx.ui = SimpleNamespace(clear=lambda: None)
    ctx.reset_debug_features()
    return ctx


def test_resp_mapping_applies_on_exit() -> None:
    ctx = make_ctx()
    with ctx:
        ctx.set_resp_mapping(messages.Failure, lambda _: messages.Success())
        ctx.set_expected_responses([messages.Success])
        ctx.actual_responses.append(messages.Failure())
    assert ctx.resp_mappings == {}


def test_resp_mapping_mismatch() -> None:
    ctx = make_ctx()
    with pytest.raises(AssertionError, match="Actually received"):
        with ctx:
            ctx.set_resp_mapping(messages.Failure, lambda _: messages.Failure())
            ctx.set_expected_responses([messages.Success])
            ctx.actual_responses.append(messages.Failure())
    assert ctx.resp_mappings == {}
