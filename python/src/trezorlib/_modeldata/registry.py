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

"""Aggregated registry of all model definitions.

Once the firmware-side generator exists, the import list below is the only
thing it needs to emit/maintain (one line per ``core/embed/models/<NAME>``)."""

from typing import Dict, Optional, Tuple

from . import D001, D002, D003, T1B1, T2B1, T2T1, T3B1, T3T1, T3T2, T3W1, ModelData

ALL: Tuple[ModelData, ...] = (
    T1B1.MODEL,
    T2T1.MODEL,
    T2B1.MODEL,
    T3T1.MODEL,
    T3T2.MODEL,
    T3B1.MODEL,
    T3W1.MODEL,
    D001.MODEL,
    D002.MODEL,
    D003.MODEL,
)

BY_INTERNAL_NAME: Dict[str, ModelData] = {m.internal_name: m for m in ALL}


def by_internal_name(internal_name: str) -> Optional[ModelData]:
    return BY_INTERNAL_NAME.get(internal_name)
