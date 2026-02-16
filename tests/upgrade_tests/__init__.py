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

from trezorlib.models import T1B1, T2T1, T3W1, by_internal_name

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
    """Create an emulator for upgrade tests.
    
    Args:
        tag: Version tag of the emulator
        model: Model name (e.g., "T3W1")
        **kwargs: Additional arguments passed to EmulatorWrapper, including:
            - tropic_enabled: Use tropic-enabled emulator binary variant (default: auto-detect)
            - Other EmulatorWrapper parameters
    
    Auto-detection:
        For models that support tropic (like T3W1), the system automatically detects
        and uses tropic-enabled emulators if they exist in the T3W1_tropic_on subdirectory.
        Otherwise, it falls back to regular emulators.
        
    Note:
        This auto-detection only happens in upgrade_emulator. Other test suites using
        EmulatorWrapper directly will use regular (faster) emulators by default.
    """
    from ..emulators import BINDIR, get_tropic_subdir, uses_tropic
    
    # Use provided model - should always be provided from @for_all decorator
    if model is None:
        raise ValueError("model parameter is required for upgrade_emulator")

    # Determine gen from model
    gen = gen_from_model(model)

    # Auto-detect tropic-enabled variant if not explicitly specified
    if "tropic_enabled" not in kwargs and tag is not None and uses_tropic(model):
        tropic_path = BINDIR / model / get_tropic_subdir(model) / f"trezor-emu-{gen}-{model}-{tag}"
        regular_path = BINDIR / model / f"trezor-emu-{gen}-{model}-{tag}"
        
        # Prefer tropic-enabled if it exists, otherwise use regular
        if tropic_path.exists():
            kwargs["tropic_enabled"] = True
            kwargs["launch_tropic_model"] = True
        elif regular_path.exists():
            kwargs["tropic_enabled"] = False
            kwargs["launch_tropic_model"] = False

    return EmulatorWrapper(
        gen,
        tag,
        model,
        **kwargs,
    )


SELECTED_GENS = [
    gen.strip() for gen in os.environ.get("TREZOR_UPGRADE_TEST", "").split(",") if gen
]

if SELECTED_GENS:
    # if any gens were selected via the environment variable, force enable all selected
    LEGACY_ENABLED = "legacy" in SELECTED_GENS
    if "core" in SELECTED_GENS:
        raise ValueError(
            "TREZOR_UPGRADE_TEST=core is ambiguous. Use core-t2t1 or core-t3w1."
        )
    CORE_T2T1_ENABLED = "core-t2t1" in SELECTED_GENS
    CORE_T3W1_ENABLED = "core-t3w1" in SELECTED_GENS
    CORE_ENABLED = CORE_T2T1_ENABLED or CORE_T3W1_ENABLED

else:
    # if no selection was provided, select those for which we have emulators
    LEGACY_ENABLED = LOCAL_BUILD_PATHS["legacy"].exists()
    CORE_ENABLED = LOCAL_BUILD_PATHS["core"].exists()
    CORE_T2T1_ENABLED = CORE_ENABLED
    CORE_T3W1_ENABLED = CORE_ENABLED


def _is_model_enabled(model) -> bool:
    if model == T1B1:
        return LEGACY_ENABLED
    if model == T2T1:
        return CORE_T2T1_ENABLED
    if model == T3W1:
        return CORE_T3W1_ENABLED
    return CORE_ENABLED


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

    models_to_test = [model for model in models_to_test if _is_model_enabled(model)]
    if not models_to_test:
        return pytest.mark.skip("no models are enabled")

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
        if model_obj is not None and _is_model_enabled(model_obj):
            params.append((tags, model_name))

    if not params:
        return pytest.mark.skip("no versions are applicable")

    return pytest.mark.parametrize("tags, model", params)
