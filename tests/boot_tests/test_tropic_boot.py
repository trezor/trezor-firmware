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


import socket
import tempfile

import pytest

from tests.emulators import LOCAL_BUILD_PATHS, ROOT, TROPIC_MODEL_CONFIGFILE
from trezorlib._internal.emulator import CoreEmulator

BUILD_PATH = LOCAL_BUILD_PATHS["core"]
TROPIC_BOOT_CONFIGS_DIR = TROPIC_MODEL_CONFIGFILE.parent / "tropic_boot_configs"
CORE_SRC_DIR = ROOT / "core" / "src"


def _free_port() -> int:
    """Ask the OS to allocate a free TCP port by binding to port 0, then return it."""
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


@pytest.mark.parametrize(
    "config_file,expect_failure",
    [
        pytest.param("config_good.yml", False, id="good"),
        pytest.param("config_bad_recoverable.yml", False, id="bad-recoverable"),
        pytest.param("config_bad_unrecoverable.yml", True, id="bad-unrecoverable"),
    ],
)
def test_tropic_boot(config_file: str, expect_failure: bool) -> None:
    config_path = TROPIC_BOOT_CONFIGS_DIR / config_file
    assert config_path.exists(), f"Missing Tropic boot fixture: {config_path}"

    with tempfile.TemporaryDirectory() as temp_dir:
        with CoreEmulator(
            profile_dir=temp_dir,
            executable=BUILD_PATH,
            workdir=CORE_SRC_DIR,
            headless=True,
            launch_tropic_model=True,
            tropic_model_configfile=str(config_path),
            tropic_model_port=_free_port(),
        ) as emulator:
            if expect_failure:
                with pytest.raises(RuntimeError, match="Emulator process died"):
                    emulator.start()
            else:
                emulator.start()
