# This file is part of the TREZOR project.
#
# Copyright (C) 2012-2017 Marek Palatinus <slush@satoshilabs.com>
# Copyright (C) 2012-2017 Pavol Rusnak <stick@satoshilabs.com>
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library.  If not, see <http://www.gnu.org/licenses/>.

import warnings

from .transport import enumerate_devices, get_transport


class TrezorDevice:
    '''
    This class is deprecated. (There is no reason for it to exist in the first
    place, it is nothing but a collection of two functions.)
    Instead, please use functions from the ``trezorlib.transport`` module.
    '''

    @classmethod
    def enumerate(cls):
        warnings.warn('TrezorDevice is deprecated.', DeprecationWarning)
        return enumerate_devices()

    @classmethod
    def find_by_path(cls, path):
        warnings.warn('TrezorDevice is deprecated.', DeprecationWarning)
        return get_transport(path, prefix_search=False)
