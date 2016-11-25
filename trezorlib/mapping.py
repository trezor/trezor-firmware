# This file is part of the TREZOR project.
#
# Copyright (C) 2012-2016 Marek Palatinus <slush@satoshilabs.com>
# Copyright (C) 2012-2016 Pavol Rusnak <stick@satoshilabs.com>
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

from . import messages_pb2 as proto

map_type_to_class = {}
map_class_to_type = {}

def build_map():
    for msg_type, i in proto.MessageType.items():
        msg_name = msg_type.replace('MessageType_', '')
        msg_class = getattr(proto, msg_name)

        map_type_to_class[i] = msg_class
        map_class_to_type[msg_class] = i

def get_type(msg):
    return map_class_to_type[msg.__class__]


def get_class(t):
    return map_type_to_class[t]

def check_missing():
    from google.protobuf import reflection

    types = [getattr(proto, item) for item in dir(proto)
             if issubclass(getattr(proto, item).__class__, reflection.GeneratedProtocolMessageType)]

    missing = list(set(types) - set(map_type_to_class.values()))

    if len(missing):
        raise Exception("Following protobuf messages are not defined in mapping: %s" % missing)

build_map()
check_missing()
