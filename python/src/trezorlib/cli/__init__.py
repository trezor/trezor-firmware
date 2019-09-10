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

import click


class ChoiceType(click.Choice):
    def __init__(self, typemap):
        super(ChoiceType, self).__init__(typemap.keys())
        self.typemap = typemap

    def convert(self, value, param, ctx):
        value = super(ChoiceType, self).convert(value, param, ctx)
        return self.typemap[value]
