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

from __future__ import annotations

import logging
import typing as t

from construct import Transformed
from construct_classes import Struct

from ..construct_helpers import Reserved

LOG = logging.getLogger(__name__)

STRICT_SANITY_CHECK_DEFAULT: bool = False

# workaround for mypy self type bug
Self = t.TypeVar("Self", bound="SanityCheckedStruct")


class SanityCheckError(Exception):
    def __init__(
        self, errors: list[str], image: SanityCheckedStruct, *args: t.Any
    ) -> None:
        self.errors = errors
        self.image = image
        super().__init__(*args)

    def get_error_message(self) -> str:
        return f"\033[1;31mERROR:\033[0m Sanity check failed!\n{self._get_formatted_message()}\n"

    def get_warning_message(self) -> str:
        return f"\033[1;33mWARNING:\033[0m Sanity check failed!\n{self._get_formatted_message()}\n"

    def _get_formatted_message(self) -> str:
        return "\n".join(f" - {err}" for err in self.errors)

    def __str__(self) -> str:
        return f"Sanity check failed!\n{self._get_formatted_message()}"


class SanityCheckedStruct(Struct):

    @classmethod
    def parse(
        cls: t.Type[Self], data: bytes, *, strict: bool = STRICT_SANITY_CHECK_DEFAULT
    ) -> Self:
        parsed_image = super().parse(data)
        try:
            parsed_image.sanity_check(data)
        except SanityCheckError as e:
            if strict:
                raise
            LOG.warning(e.get_warning_message())
        return parsed_image

    def sanity_check(self, image: bytes, errors: t.Sequence[str] = ()) -> None:
        """Sanity check

        - Parsing and rebuilding does not modify the image bytes.
        - Reserved fields are parsed correctly and contain only zeroes.
        """

        _errors: list[str] = list(errors)
        is_ok = True

        # Parsing and rebuilding does not modify the image bytes
        rebuilt_image = self.build()
        if image != rebuilt_image:
            _errors.append('"Parsing and rebuilding image" sanity check failed.')
            is_ok = False

        is_ok = is_ok and self._subcons_sanity_check(_errors)

        if not is_ok:
            raise SanityCheckError(_errors, self)

    def _subcons_sanity_check(self, errors: list[str]) -> bool:
        try:
            subcon = self.SUBCON

            # VendorTrust is wrapped multiple times in `Transformed`
            while isinstance(subcon, Transformed):
                subcon = subcon.subcon

            subcon_fields: t.ItemsView[str, t.Any] = subcon._subcons.items()  # type: ignore [Cannot access attribute]
        except Exception as e:
            errors.append(f"Failed to parse subcon fields. {e}")
            return False

        is_ok = True
        for name, value in subcon_fields:

            # Skip private fields
            if name[0] == "_":
                continue

            # Public fields should be present in the class
            try:
                field_data = getattr(self, name)
            except AttributeError:
                errors.append(f"Missing subcon field: \033[1m{name}\033[0m")
                is_ok = False
                continue

            # Check that `Reserved` fields are all zeroes.
            # Extraction to `inner` is necessary because `value` is internally packed into `construct.core.Renamed`
            # and `isinstance(value, Reserved)` returns False even for `Reserved` fields.
            inner = value.subcon if hasattr(value, "subcon") else value
            if isinstance(inner, Reserved):
                if not all(v == 0 for v in field_data):
                    try:
                        value_str = field_data.hex()
                    except Exception:
                        value_str = str(field_data)
                    errors.append(
                        f"Reserved field \033[1m{name}\033[0m is not zero: {value_str}"
                    )
                    is_ok = False
                continue

            # Recursive check
            if isinstance(field_data, SanityCheckedStruct):
                is_ok = is_ok and field_data._subcons_sanity_check(errors)

        return is_ok
