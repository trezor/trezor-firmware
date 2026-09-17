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

import logging
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest

from trezorlib._internal.emulator import TropicModel

from ..emulators import (
    TROPIC_MODEL_CONFIGFILE,
    TROPIC_MODEL_CONFIGFILE_OLD,
    TROPIC_OLD_CONFIG_UNTIL_VERSION,
    delete_profile,
    get_logfile,
    is_tropic_capable_model,
)

LOG = logging.getLogger(__name__)


def _get_tropic_model_configfile(tag: str | None) -> Path:
    if tag is not None and tag.startswith("v"):
        tag_version = tag[1:].partition("-")[0]
        if len(tag_version.split(".")) == 3:
            version_tuple = tuple(int(i) for i in tag_version.split("."))
            if version_tuple <= TROPIC_OLD_CONFIG_UNTIL_VERSION:
                return TROPIC_MODEL_CONFIGFILE_OLD
    return TROPIC_MODEL_CONFIGFILE


# This fixture is very similar to `tropic_model` from the parent directory, but has a "function"
# scope instead of session.
@pytest.fixture
def shared_profile_dir(request) -> Generator[str, Any, Any]:
    # Use the default port because before 2.9.4 it was not configurable.
    # This means upgrade tests currently can't run in multiple threads for T3W1.
    tropic_model_port = 28992
    model = request.node.callspec.params["model"]
    start_tropic_model = is_tropic_capable_model(model)

    profile_dir = tempfile.TemporaryDirectory(
        prefix="trezor-upgrade-", delete=delete_profile()
    )
    LOG.debug(
        f"Test profile dir: {profile_dir.name} (delete: {delete_profile()}), start_tropic: {start_tropic_model}"
    )

    with profile_dir as path:
        # do not start tropic model when not supported
        if not start_tropic_model:
            yield path
            return

        tag = request.node.callspec.params["tag"]
        with TropicModel(
            profile_dir=path,
            configfile=_get_tropic_model_configfile(tag),
            port=tropic_model_port,
            logfile=get_logfile("trezor-tropic-model.log", Path(profile_dir.name)),
        ) as tropic_model:
            tropic_model.start()
            yield path
