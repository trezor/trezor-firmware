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

import pytest

from ..emulators import ALL_TAGS, LOCAL_BUILD_PATHS

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


def for_all(*args, legacy_minimum_version=(1, 0, 0), core_minimum_version=(2, 0, 0)):
    """Parametrizing decorator for test cases.

    Usage example:

    >>> @for_all()
    >>> def test_runs_for_all_old_versions(gen, tag):
    >>>     assert True

    Arguments can be "core" and "legacy", and you can specify core_minimum_version and
    legacy_minimum_version as triplets.

    The test function should have arguments `gen` ("core" or "legacy") and `tag`
    (version tag usable in EmulatorWrapper call)
    """
    if not args:
        args = ("core", "legacy")

    # If any gens were selected, use them. If none, select all.
    enabled_gens = SELECTED_GENS or args

    all_params = []
    for gen in args:
        if gen == "legacy":
            minimum_version = legacy_minimum_version
        elif gen == "core":
            minimum_version = core_minimum_version
        else:
            raise ValueError

        if gen not in enabled_gens:
            continue
        try:
            for tag in ALL_TAGS[gen]:
                if tag.startswith("v"):
                    tag_version = tag[1:]
                    if "-" in tag:  # contains revision
                        tag_version = tag[1:-9]
                    tag_version = tuple(int(n) for n in tag_version.split("."))
                    if tag_version < minimum_version:
                        continue
                all_params.append((gen, tag))

            # at end, add None tag, which is the current master
            all_params.append((gen, None))
        except KeyError:
            pass

    if not all_params:
        return pytest.mark.skip("no versions are applicable")

    return pytest.mark.parametrize("gen, tag", all_params)
