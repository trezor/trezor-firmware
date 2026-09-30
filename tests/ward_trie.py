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

"""Moved to `trezorlib.ward_trie`; this re-export keeps the tests' imports working.

The host trie lived here only because `trezorlib` had none. A real host needs exactly it, so it
is part of the library now. Import from `trezorlib.ward_trie` in new code; this shim can go once
the existing importers are migrated.
"""

from trezorlib.ward_trie import *  # noqa: F401,F403
from trezorlib.ward_trie import __all__  # noqa: F401
