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

import importlib.metadata
import warnings


def __getattr__(name: str) -> str:
    if name == "__version__":
        warnings.warn(
            "__version__ is deprecated and will be removed in 0.15.0, use importlib.metadata.version('trezor') instead",
            DeprecationWarning,
        )
        return importlib.metadata.version("trezor")
    raise AttributeError(f"module {__name__} has no attribute {name}")
