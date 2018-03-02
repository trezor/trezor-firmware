# This file is part of the TREZOR project.
#
# Copyright (C) 2012-2016 Marek Palatinus <slush@satoshilabs.com>
# Copyright (C) 2012-2016 Pavol Rusnak <stick@satoshilabs.com>
# Copyright (C) 2016      Jochen Hoenicke <hoenicke@gmail.com>
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

from __future__ import absolute_import


class TransportException(Exception):
    pass


class Transport(object):

    def __init__(self):
        self.session_counter = 0

    def session_begin(self):
        if self.session_counter == 0:
            self.open()
        self.session_counter += 1

    def session_end(self):
        self.session_counter = max(self.session_counter - 1, 0)
        if self.session_counter == 0:
            self.close()

    def open(self):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError
