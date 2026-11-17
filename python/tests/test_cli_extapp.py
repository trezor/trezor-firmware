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

from pathlib import Path

import pytest

from trezorlib.cli.extapp import _select_app
from trezorlib.extapp import AppHeader

APP_ID = "test.example.com"
PAYLOAD = b"\x01\x02\x03\x04"


def write_app(app_dir: Path, version: tuple[int, int, int, int]) -> Path:
    header = AppHeader.SUBCON.build(
        dict(
            header_size=512,
            id=APP_ID,
            name="Test",
            vendor="Example",
            model="T3W1",
            version=version,
            sdk_version=(0, 1, 0, 0),
            abi_version=1,
            target_arch=0,
            app_ring=2,
            language=0,
            code_size=len(PAYLOAD),
            data_size=1024,
            chunk_hash=b"\x00" * 32,
            chunk_size=4,
            curves=[],
            paths=[],
            ipc_buffer_size=4096,
        )
    )
    path = app_dir / f"{APP_ID}_{'.'.join(map(str, version))}.tapp"
    path.write_bytes(header + PAYLOAD)
    return path


def test_select_app_newest(tmp_path: Path) -> None:
    # '10.0' sorts before '2.0' by name
    for version in ((1, 0, 0, 0), (2, 0, 0, 0), (10, 0, 0, 0)):
        write_app(tmp_path, version)
    path, binary = _select_app(tmp_path, APP_ID)
    assert path.name == f"{APP_ID}_10.0.0.0.tapp"
    assert binary == path.read_bytes()


def test_select_app_by_header_version(tmp_path: Path) -> None:
    # the version comes from the header, not from the file name
    write_app(tmp_path, (1, 0, 0, 0)).rename(tmp_path / f"{APP_ID}_9.tapp")
    write_app(tmp_path, (2, 0, 0, 0)).rename(tmp_path / f"{APP_ID}_1.tapp")
    path, _ = _select_app(tmp_path, APP_ID)
    assert path.name == f"{APP_ID}_1.tapp"


def test_select_app_missing(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="No app found"):
        _select_app(tmp_path, APP_ID)
