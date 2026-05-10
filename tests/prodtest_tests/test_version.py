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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

from __future__ import annotations

import re

from trezorlib.prodtest.prodtest_client import Cmd, ProdtestClient, ProdtestCommand


def test_prodtest_version_format(prodtest_client: ProdtestClient) -> None:
    """prodtest-version should return a version in major.minor.patch.build format."""
    resp = prodtest_client.command_ok(ProdtestCommand(Cmd.PRODTEST_VERSION))
    assert re.match(
        r"\d+\.\d+\.\d+\.\d+", resp.args
    ), f"Unexpected version format: {resp.args}"


def test_boardloader_version_format(prodtest_client: ProdtestClient) -> None:
    """boardloader-version should return a version in major.minor.patch format."""
    resp = prodtest_client.command_ok(ProdtestCommand(Cmd.BOARDLOADER_VERSION))
    assert re.match(
        r"\d+\.\d+\.\d+", resp.args
    ), f"Unexpected version format: {resp.args}"


def test_prodtest_model(prodtest_client: ProdtestClient) -> None:
    """prodtest-model should return an internal model name."""
    assert prodtest_client.model is not None
