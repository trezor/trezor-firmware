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

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from trezorlib import models

if TYPE_CHECKING:
    from _pytest.mark.structures import MarkDecorator


HERE = Path(__file__).resolve().parent
COMMON_FIXTURES_DIR = HERE / "fixtures"


def parametrize_using_common_fixtures(*paths: str) -> "MarkDecorator":
    fixtures = []
    for path in paths:
        fixtures.append(json.loads((COMMON_FIXTURES_DIR / path).read_text()))

    tests = []
    for fixture in fixtures:
        for test in fixture["tests"]:
            test_id = test.get("name")
            if not test_id:
                test_id = test.get("description")
                if test_id is not None:
                    test_id = test_id.lower().replace(" ", "_")

            skip_models = test.get("skip_models", [])
            skiplist = []
            # TODO: genericify this
            for skip_model in skip_models:
                if skip_model == "t3t1":
                    skiplist.append(models.T3T1)
                if skip_model == "t3w1":
                    skiplist.append(models.T3W1)
            if skiplist:
                extra_marks = [pytest.mark.models(skip=skiplist)]
            else:
                extra_marks = []

            if test.get("experimental"):
                extra_marks.append(pytest.mark.experimental)

            tests.append(
                pytest.param(
                    test["parameters"],
                    test["result"],
                    marks=[
                        pytest.mark.setup_client(
                            passphrase=fixture["setup"]["passphrase"],
                            mnemonic=fixture["setup"]["mnemonic"],
                        )
                    ]
                    + extra_marks,
                    id=test_id,
                )
            )

    return pytest.mark.parametrize("parameters, result", tests)
