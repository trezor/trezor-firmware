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

import shutil
import tempfile
from pathlib import Path

import pytest

from ..emulators import EmulatorWrapper, stop_shared_tropic_model

TROPIC_BOOT_CONFIGS_DIR = (
    Path(__file__).resolve().parent.parent / "tropic_model" / "tropic_boot_configs"
)
TROPIC_MODEL_DIR = TROPIC_BOOT_CONFIGS_DIR.parent


@pytest.mark.models("T3W1")
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
    if not config_path.exists():
        pytest.fail(f"Config file not yet available: {config_path}")

    profile = tempfile.TemporaryDirectory()
    # Copy PEM support files so model_server can resolve relative key paths in the config.
    for pem in TROPIC_MODEL_DIR.glob("*.pem"):
        shutil.copy(pem, Path(profile.name) / pem.name)
    shutil.copy(config_path, Path(profile.name) / "tropic_model_config_output.yml")

    wrapper = None
    try:
        wrapper = EmulatorWrapper("T3W1", profile_dir=profile)
        if expect_failure:
            with pytest.raises(RuntimeError, match="Emulator process died"):
                with wrapper:
                    pass
            # __exit__ was not called (raised in __enter__), clean up manually
            wrapper.emulator.stop()
        else:
            with wrapper:
                pass
    finally:
        stop_shared_tropic_model(profile.name)
        profile.cleanup()
