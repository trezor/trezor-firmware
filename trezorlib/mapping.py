# This file is part of the Trezor project.
#
# Copyright (C) 2012-2018 SatoshiLabs and contributors
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

from . import messages

map_type_to_class = {}
map_class_to_type = {}


def build_map():
    for msg_name in dir(messages.MessageType):
        if msg_name.startswith("__"):
            continue

        try:
            msg_class = getattr(messages, msg_name)
        except AttributeError:
            raise ValueError(
                "Implementation of protobuf message '%s' is missing" % msg_name
            )

        if msg_class.MESSAGE_WIRE_TYPE != getattr(messages.MessageType, msg_name):
            raise ValueError(
                "Inconsistent wire type and MessageType record for '%s'" % msg_class
            )

        register_message(msg_class)


def register_message(msg_class):
    if msg_class.MESSAGE_WIRE_TYPE in map_type_to_class:
        raise Exception(
            "Message for wire type %s is already registered by %s"
            % (msg_class.MESSAGE_WIRE_TYPE, get_class(msg_class.MESSAGE_WIRE_TYPE))
        )

    map_class_to_type[msg_class] = msg_class.MESSAGE_WIRE_TYPE
    map_type_to_class[msg_class.MESSAGE_WIRE_TYPE] = msg_class


def get_type(msg):
    return map_class_to_type[msg.__class__]


def get_class(t):
    return map_type_to_class[t]


build_map()
