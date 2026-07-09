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
import re
from pathlib import Path
from typing import List, Tuple

import pytest
from _pytest.mark.structures import MarkDecorator

from trezorlib.models import T1B1, T2T1, T3W1, by_internal_name

from ..emulators import LOCAL_BUILD_PATHS, get_tags

ALL_TAGS = get_tags()


SELECTED_MODELS = [
    m.strip().upper()
    for m in os.environ.get("TREZOR_UPGRADE_TEST", "").split(",")
    if m.strip()
]


def _detect_local_core_build_model() -> str | None:
    build_dir = Path(LOCAL_BUILD_PATHS["core"]).parent
    if not build_dir.exists():
        return None

    for trezorhal_path in sorted(build_dir.rglob("trezorhal.rs")):
        try:
            content = trezorhal_path.read_text()
        except OSError:
            continue

        match = re.search(r'MODEL_INTERNAL_NAME: .* = b"([A-Z0-9]+)\\0";', content)
        if match:
            return match.group(1)

    return None


if SELECTED_MODELS:
    # Validate all selected model names
    for name in SELECTED_MODELS:
        if by_internal_name(name) is None:
            raise ValueError(
                f"Unknown model in TREZOR_UPGRADE_TEST: {name}. "
                "Use model names like T1B1, T2T1, T3W1."
            )

    _enabled_models = {by_internal_name(name) for name in SELECTED_MODELS}
    LEGACY_ENABLED = T1B1 in _enabled_models
    CORE_T2T1_ENABLED = T2T1 in _enabled_models
    CORE_T3W1_ENABLED = T3W1 in _enabled_models
    # Models without their own upgrade emulators (e.g. T3B1, T3T1) enable
    # the core path so that persistence tests using core_only still run.
    CORE_ENABLED = (
        CORE_T2T1_ENABLED
        or CORE_T3W1_ENABLED
        or bool(_enabled_models - {T1B1, T2T1, T3W1})
    )

else:
    # if no selection was provided, select those for which we have emulators
    LEGACY_ENABLED = LOCAL_BUILD_PATHS["legacy"].exists()
    CORE_ENABLED = LOCAL_BUILD_PATHS["core"].exists()
    detected_core_model = _detect_local_core_build_model() if CORE_ENABLED else None

    # Fail explicitly if local core build exists but model cannot be detected.
    # Silently defaulting to T2T1 for unknown builds masks configuration issues.
    if CORE_ENABLED and detected_core_model is None:
        raise ValueError(
            "Local core emulator build detected but model could not be determined. "
            "Please ensure trezorhal.rs exists with MODEL_INTERNAL_NAME, "
            "or specify TREZOR_UPGRADE_TEST=T2T1|T3W1 explicitly."
        )

    CORE_T2T1_ENABLED = CORE_ENABLED and detected_core_model != "T3W1"
    CORE_T3W1_ENABLED = CORE_ENABLED and detected_core_model == "T3W1"


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
    t1b1_minimum_version: Tuple[int, int, int] = (1, 0, 0),
    t2t1_minimum_version: Tuple[int, int, int] = (2, 0, 0),
    # Intentionally starts at 2.9.3 for T3W1 upgrade coverage.
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
            minimum_version = t1b1_minimum_version
        elif model == T3W1:
            minimum_version = t3w1_minimum_version
        elif model == T2T1:
            minimum_version = t2t1_minimum_version
        else:
            minimum_version = t2t1_minimum_version

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

    return pytest.mark.parametrize("tag, model", sorted(all_params))


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
