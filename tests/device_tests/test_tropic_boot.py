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

import os
import shutil
import socket
import tempfile
from pathlib import Path

import pytest
import xdist

from ..emulators import EmulatorWrapper, stop_shared_tropic_model

TROPIC_BOOT_CONFIGS_DIR = (
    Path(__file__).resolve().parent.parent / "tropic_model" / "tropic_boot_configs"
)
TROPIC_MODEL_DIR = TROPIC_BOOT_CONFIGS_DIR.parent

pytestmark = [
    pytest.mark.skipif(
        os.environ.get("TREZOR_MODEL", "").upper() != "T3W1",
        reason="Only runs on T3W1",
    ),
]  # we cannot use @pytest.mark.model("T3W1") here, because the test needs to run before
# the emulator is started, and the model is only detected during emulator startup


@pytest.mark.parametrize(
    "config_file,expect_failure",
    [
        pytest.param("config_good.yml", False, id="good"),
        pytest.param("config_bad_recoverable.yml", False, id="bad-recoverable"),
        pytest.param("config_bad_unrecoverable.yml", True, id="bad-unrecoverable"),
    ],
)
def test_tropic_boot(
    request: pytest.FixtureRequest, config_file: str, expect_failure: bool
) -> None:
    config_path = TROPIC_BOOT_CONFIGS_DIR / config_file
    assert config_path.exists(), f"Missing Tropic boot fixture: {config_path}"

    profile = tempfile.TemporaryDirectory()
    # Copy PEM support files so model_server can resolve relative key paths in the config.
    for pem in TROPIC_MODEL_DIR.glob("*.pem"):
        shutil.copy(pem, Path(profile.name) / pem.name)
    shutil.copy(config_path, Path(profile.name) / "tropic_model_config_output.yml")

    # Derive the real xdist worker ID so this test uses the same port-allocation
    # scheme as all other tests. When running outside xdist (single-process),
    # get_xdist_worker_id returns "master", which we map to 0.
    raw_worker_id = xdist.get_xdist_worker_id(request)
    worker_id = int(raw_worker_id[2:]) if raw_worker_id.startswith("gw") else 0

    # Ask the OS for free ports for the tropic model server and for the emulator
    # itself. We cannot use _get_tropic_model_port(worker_id) or _get_port(worker_id)
    # here because those ports are already bound by the session-scoped emulator
    # fixture running on this same worker.
    with socket.socket() as s1, socket.socket() as s2:
        s1.bind(("", 0))
        s2.bind(("", 0))
        tropic_port = s1.getsockname()[1]
        emulator_port = s2.getsockname()[1]

    wrapper = None
    try:
        wrapper = EmulatorWrapper(
            "T3W1",
            profile_dir=profile,
            worker_id=worker_id,
            tropic_model_port_override=tropic_port,
            port_override=emulator_port,
        )
        if expect_failure:
            with pytest.raises(RuntimeError, match="Emulator process died"):
                with wrapper:
                    pass
            # __exit__ was not called (raised in __enter__) => clean up manually
            wrapper.emulator.stop()
        else:
            with wrapper:
                pass
    finally:
        stop_shared_tropic_model(profile.name)
        profile.cleanup()
