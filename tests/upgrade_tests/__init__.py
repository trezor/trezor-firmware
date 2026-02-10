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
import tempfile
from contextlib import contextmanager
from typing import List, Tuple

import pytest
from _pytest.mark.structures import MarkDecorator

from trezorlib.models import (
    CORE_MODELS, 
    LEGACY_MODELS, 
    T1B1, 
    T2T1, 
    T3W1, 
    by_internal_name
)

from ..emulators import (
    ALL_TAGS,
    LOCAL_BUILD_PATHS,
    EmulatorWrapper,
    gen_from_model,
    stop_shared_tropic_model,
)


@contextmanager
def shared_profile_dir() -> tempfile.TemporaryDirectory:
    profile_dir = tempfile.TemporaryDirectory()
    try:
        yield profile_dir
    finally:
        stop_shared_tropic_model(profile_dir.name)
        if os.environ.get("TREZOR_KEEP_PROFILE_DIR") != "1":
            profile_dir.cleanup()


def upgrade_emulator(
    tag: str | None = None,
    model: str | None = None,
    **kwargs,
) -> EmulatorWrapper:
    # Use provided model or get from environment, default to T3W1
    model_name = model or os.environ.get("TREZOR_MODEL") or "T3W1"
    
    # Determine gen from model
    gen = gen_from_model(model_name)
    
    # Only launch Tropic model for T3W1
    disable_tropic = os.environ.get("TREZOR_DISABLE_TROPIC_MODEL") == "1"
    launch_tropic = (model_name == "T3W1") and not disable_tropic
    
    return EmulatorWrapper(
        gen,
        tag,
        model,
        launch_tropic_model=launch_tropic,
        **kwargs,
    )

SELECTED_GENS = [
    gen.strip() for gen in os.environ.get("TREZOR_UPGRADE_TEST", "").split(",") if gen
]

if SELECTED_GENS:
    # if any gens were selected via the environment variable, force enable all selected
    LEGACY_ENABLED = "legacy" in SELECTED_GENS
    CORE_ENABLED = "core" in SELECTED_GENS

else:
    # if no selection was provided, select those for which we have emulators
    LEGACY_ENABLED = LOCAL_BUILD_PATHS["legacy"].exists()
    CORE_ENABLED = LOCAL_BUILD_PATHS["core"].exists()


legacy_only = pytest.mark.skipif(
    not LEGACY_ENABLED, reason="This test requires legacy emulator"
)

core_only = pytest.mark.skipif(
    not CORE_ENABLED, reason="This test requires core emulator"
)


def version_from_tag(tag: str | None) -> tuple | None:
    if tag is None or not tag.startswith("v"):
        return None

    # Strip initial "v" and optional revision from the tag string.
    tag_version = tag[1:].partition("-")[0]

    # Translate string to an integer tuple.
    return tuple(int(n) for n in tag_version.split("."))


def for_all(
    *args: str,
    legacy_minimum_version: Tuple[int, int, int] = (1, 0, 0),
    core_minimum_version: Tuple[int, int, int] = (2, 0, 0),
    t3w1_minimum_version: Tuple[int, int, int] = (2, 9, 3),
) -> "MarkDecorator":
    """Parametrizing decorator for test cases.

    Usage example:

    >>> @for_all("T1B1", "T2T1", "T3W1")
    >>> def test_runs_for_all_models(tag, model):
    >>>     assert True

    Arguments should be trezor model names (e.g. "T1B1", "T2T1", "T3W1").
    If no arguments provided, defaults to all supported models.
    You can specify minimum versions for each model type.

    The test function should have arguments `tag` (version tag) and `model` (internal model name).
    """
    if not ALL_TAGS:
        raise ValueError(
            "No files found. Use download_emulators.sh to download emulators."
        )
    
    # Map model names to TrezorModel objects
    models_to_test = []
    for item in args:
        model_obj = by_internal_name(item)
        if model_obj is not None:
            models_to_test.append(model_obj)
        else:
            raise ValueError(f"Unknown model: {item}")

    # If no args provided, default to all supported models
    if not args:
        models_to_test = [T1B1, T2T1, T3W1]

    all_params: set[tuple[str | None, str | None]] = set()
    
    for model in models_to_test:
        # Determine minimum version based on model
        if model == T1B1:
            minimum_version = legacy_minimum_version
        elif model == T3W1:
            minimum_version = t3w1_minimum_version            
        elif model == T2T1:
            minimum_version = core_minimum_version
        else:
            minimum_version = core_minimum_version

        try:
            for tag in ALL_TAGS[model.internal_name]:
                tag_version = version_from_tag(tag)
                if tag_version is not None and tag_version < minimum_version:
                    continue
                all_params.add((tag, model.internal_name))

        except KeyError:
            pass

    if not all_params:
        return pytest.mark.skip("no versions are applicable")

    return pytest.mark.parametrize("tag, model", all_params)


def for_tags(*args: Tuple[str, List[str]]) -> "MarkDecorator":
    """Parametrizing decorator for tests that need specific version tags.
    
    Usage: @for_tags(("T1B1", ["v1.7.0", "v1.8.0"]))
    
    Returns parameters: (tags, model)
    """
    params = []
    for model_name, tags in args:
        # Map model name to model object to get gen
        model_obj = by_internal_name(model_name)
        if model_obj is not None:
            params.append((tags, model_name))
    
    if not params:
        return pytest.mark.skip("no versions are applicable")
    
    return pytest.mark.parametrize("tags, model", params)
