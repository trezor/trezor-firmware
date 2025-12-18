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
from typing import List, Tuple

import pytest
from _pytest.mark.structures import MarkDecorator

from trezorlib.models import (
    CORE_MODELS,
    LEGACY_MODELS,
    T1B1,
    T2T1,
    T3W1,
    by_internal_name,
)

from ..emulators import ALL_TAGS, LOCAL_BUILD_PATHS, gen_from_model

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

    >>> @for_all()
    >>> def test_runs_for_all_old_versions(gen, tag, model):
    >>>     assert True

    Arguments can be trezor models (e.g."T1B1" and "T2T1") or aliases "core" and "legacy",
    and you can specify core_minimum_version, legacy_minimum_version and t3w1_minimum_version
    as triplets.

    The test function should have arguments `gen` ("core" or "legacy") and `tag`
    (version tag usable in EmulatorWrapper call)
    """
    if not ALL_TAGS:
        raise ValueError(
            "No files found. Use download_emulators.sh to download emulators."
        )
    models = []
    gens = set()
    for item in args:
        if item == "core":
            models.extend(CORE_MODELS)
            gens.add("core")
        elif item == "legacy":
            models.extend(LEGACY_MODELS)
            gens.add("legacy")
        else:
            models.append(by_internal_name(item))
            gens.add(gen_from_model(item))

    if not args:
        gens = ["core", "legacy"]
        models = [T1B1, T2T1, T3W1]

    # If any gens were selected, use them. If none, select all.
    enabled_gens = SELECTED_GENS or list(gens)

    all_params: set[tuple[str, str | None, str | None]] = set()
    for model in models:
        if model in LEGACY_MODELS:
            minimum_version = legacy_minimum_version
        elif model == T3W1:
            minimum_version = t3w1_minimum_version
        elif model in CORE_MODELS:
            minimum_version = core_minimum_version
        else:
            raise ValueError

        gen = gen_from_model(model.internal_name)
        if gen not in enabled_gens:
            continue
        try:
            for tag in ALL_TAGS[model.internal_name]:
                tag_version = version_from_tag(tag)
                if tag_version is not None and tag_version < minimum_version:
                    continue
                all_params.add((gen, tag, model.internal_name))

            # At the end, add (gen, None, None), which is the current master.
            # The same (gen, None, None) can be added multiple times as there are
            # more models than gens. That is why all_params is defined as a set.
            all_params.add((gen, None, None))
        except KeyError:
            pass

    if not all_params:
        return pytest.mark.skip("no versions are applicable")

    return pytest.mark.parametrize("gen, tag, model", all_params)


def for_tags(*args: Tuple[str, List[str]]) -> "MarkDecorator":
    enabled_gens = SELECTED_GENS or ("core", "legacy")
    return pytest.mark.parametrize(
        "gen, tags", [(gen, tags) for gen, tags in args if gen in enabled_gens]
    )
